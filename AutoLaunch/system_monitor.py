#!/usr/bin/env python3
"""One iTerm2 process for CPU usage and optional CPU temperature only.

Run with --diagnose outside iTerm2. See README.md for metric definitions,
sensor limitations, installation and the optional system_monitor.json file.
"""

import argparse
import asyncio
import ctypes as C
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time


DEFAULTS = {"interval": 5, "sensor_interval": 30, "enable_istats": False,
            "istats_path": None}


def load_config(path):
    config = DEFAULTS.copy()
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) - set(DEFAULTS):
            raise ValueError("Unknown configuration keys; see system_monitor.example.json")
        config.update(data)
    for key, low, high in (("interval", 5, 60), ("sensor_interval", 30, 3600)):
        value = config[key]
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not low <= value <= high):
            raise ValueError("{} must be between {} and {} seconds".format(key, low, high))
    if type(config["enable_istats"]) is not bool:
        raise ValueError("enable_istats must be true or false")
    path = config["istats_path"]
    if path is not None and (not isinstance(path, str) or not os.path.isabs(path)):
        raise ValueError("istats_path must be an absolute executable path or null")
    return config


class NativeReader:
    def __init__(self):
        if sys.platform != "darwin":
            raise OSError("This monitor requires macOS")
        self.lib = C.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        self.lib.mach_host_self.argtypes = []
        self.lib.mach_host_self.restype = C.c_uint32
        self.host = self.lib.mach_host_self()  # Reuse one send right for the process lifetime.
        self.lib.host_statistics.argtypes = [C.c_uint32, C.c_int, C.c_void_p, C.POINTER(C.c_uint32)]
        self.lib.host_statistics.restype = C.c_int

    def cpu(self):
        ticks = (C.c_uint32 * 4)()  # user, system, idle, nice
        count = C.c_uint32(4)
        code = self.lib.host_statistics(self.host, 3, C.byref(ticks), C.byref(count))
        if code or count.value != 4:
            raise OSError("Mach CPU statistics unavailable (result {})".format(code))
        return tuple(ticks)

    def read(self):
        try:
            return {"cpu_ticks": self.cpu(), "errors": {}}
        except (OSError, AttributeError, ValueError) as exc:
            return {"cpu_ticks": None, "errors": {"cpu_ticks": str(exc)}}


def cpu_percent(previous, current):
    if previous is None or current is None:
        return None
    # Mach CPU counters are unsigned 32-bit, including on arm64.
    delta = [(new - old) & 0xffffffff for old, new in zip(previous, current)]
    if any(value > 0x7fffffff for value in delta) or sum(delta) == 0:
        return None  # Reset/invalid sample, rather than a spurious 100%.
    return 100.0 * (sum(delta) - delta[2]) / sum(delta)


class CoreSampler:
    def __init__(self, reader, interval=5, clock=time.monotonic):
        self.reader, self.interval, self.clock = reader, interval, clock
        self.last_time = None
        self.previous = None
        self.cached = None

    def get(self):
        now = self.clock()
        if self.last_time is not None and now - self.last_time < self.interval:
            return self.cached
        current = self.reader.read()
        elapsed = now - self.last_time if self.last_time is not None else 0
        previous = self.previous if 0 < elapsed <= max(30, self.interval * 3) else None
        current["cpu_percent"] = cpu_percent(
            previous.get("cpu_ticks") if previous else None, current.get("cpu_ticks"))
        self.last_time, self.previous, self.cached = now, current, current
        return current


def find_istats(explicit=None):
    if explicit is not None:
        candidates = [explicit]  # A bad explicit path must not silently select another install.
    else:
        candidates = [shutil.which("istats"), "/opt/homebrew/bin/istats",
                      "/opt/homebrew/opt/ruby/bin/istats", "/usr/local/bin/istats",
                      "/usr/local/opt/ruby/bin/istats"]
    return next((path for path in candidates
                 if path and os.path.isfile(path) and os.access(path, os.X_OK)), None)


async def run_command(argv, timeout=2, limit=8192):
    """Bound runtime/output and reap the whole process group on failure/cancellation."""
    env = dict(os.environ, LC_ALL="C", LANG="C")
    proc = await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, env=env, start_new_session=True)

    async def read():
        data = bytearray()
        while True:
            chunk = await proc.stdout.read(min(4096, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("Sensor output exceeds {} bytes".format(limit))
        code = await proc.wait()
        if code:
            raise OSError("Sensor command exited with status {}".format(code))
        return data.decode("utf-8", errors="strict")

    try:
        return await asyncio.wait_for(read(), timeout)
    except BaseException:
        # Also kill descendants holding stdout open after the parent exits.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        # Drain/discard buffered bytes: Process.wait() alone can hang when a
        # flooded stdout transport is paused, even after SIGKILL.
        while await proc.stdout.read(4096):
            pass
        await proc.wait()
        raise


def parse_sensor(text):
    lines = text.strip().splitlines()
    if len(lines) != 1:
        raise ValueError("Missing or unexpected temperature reading")
    # --value-only promises a plain number; do not extract numbers from errors.
    if not re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", lines[0]):
        raise ValueError("Non-numeric sensor output")
    value = float(lines[0])
    if not math.isfinite(value) or not 0 < value <= 150:
        raise ValueError("Sensor reading outside sanity bounds")
    return value


class SensorSampler:
    def __init__(self, config, runner=run_command, clock=time.monotonic):
        self.enabled = config["enable_istats"]
        self.path = find_istats(config["istats_path"]) if self.enabled else None
        self.interval, self.runner, self.clock = config["sensor_interval"], runner, clock
        self.lock = asyncio.Lock()
        self.cache = None
        self.next_read = -1
        self.failures = 0

    async def get(self):
        if not self.enabled:
            return {"value": None, "error": "iStats disabled; hardware support unverified"}
        if not self.path:
            return {"value": None, "error": "iStats executable not found; configure istats_path and restart"}
        async with self.lock:
            if self.clock() < self.next_read:
                return self.cache
            delay = self.interval
            try:
                value = parse_sensor(await self.runner([self.path, "cpu", "temp", "--value-only"]))
                result = {"value": value, "error": None}
                self.failures = 0
            except (OSError, ValueError, asyncio.TimeoutError) as exc:
                # Never serve the old reading as if it were current after an error.
                result = {"value": None, "error": str(exc) or "Sensor command timed out"}
                self.failures = min(self.failures + 1, 4)
                delay = max(self.interval, min(300, 30 * 2 ** self.failures))
            self.cache, self.next_read = result, self.clock() + delay
            return result


async def register_components(connection, api, core, sensors, config):
    async def cpu(knobs=None):
        value = core.get()["cpu_percent"]
        return "CPU N/A" if value is None else "CPU {:.0f}%".format(value)

    async def temperature(knobs=None):
        value = (await sensors.get())["value"]
        return "Temp N/A" if value is None else "CPU {:.1f}°C".format(value)

    entries = [
        ("CPU Usage", "cpu_usage", cpu, "CPU 25%", config["interval"],
         "System CPU busy time, normalized to 0–100% across all cores; first sample is N/A."),
        ("CPU Temperature", "cpu_temperature", temperature, "Temp N/A", config["sensor_interval"],
         "Optional iStats CPU sensor; disabled by default, no Apple Silicon/M6 support guarantee. See --diagnose."),
    ]
    for name, identifier, callback, exemplar, cadence, description in entries:
        # Unique RPC names are required when registering several components in one process.
        callback.__name__ = "system_monitor_" + identifier
        component = api.StatusBarComponent(
            short_description=name, detailed_description=description, knobs=[],
            exemplar=exemplar, update_cadence=cadence,
            identifier="vxider.iterm-components." + identifier)
        await component.async_register(connection, api.StatusBarRPC(callback), timeout=6)


async def diagnose(config, count):
    core = CoreSampler(NativeReader(), config["interval"])
    sensors = SensorSampler(config)
    for index in range(count):
        data = dict(core.get())
        data["temperature"] = await sensors.get()
        print(json.dumps(data, ensure_ascii=False, allow_nan=False), flush=True)
        if index + 1 < count:
            await asyncio.sleep(config["interval"])


def entrypoint():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose", action="store_true", help="print JSON without importing iterm2")
    parser.add_argument("--samples", type=int, default=2, help="diagnostic samples, 1–720 (default 2)")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_suffix(".json"))
    args = parser.parse_args()
    if not 1 <= args.samples <= 720:
        parser.error("--samples must be between 1 and 720")
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.diagnose:
        asyncio.run(diagnose(config, args.samples))
        return
    import iterm2

    async def main(connection):
        await register_components(connection, iterm2, CoreSampler(NativeReader(), config["interval"]),
                                  SensorSampler(config), config)

    iterm2.run_forever(main)


if __name__ == "__main__":
    entrypoint()
