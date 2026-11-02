#!/usr/bin/env python3
"""One iTerm2 process for macOS monitoring; stdlib only except the iTerm2 API.

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


GIB = 1024 ** 3
MIB = 1024 ** 2
PRESSURE = {1: "Normal", 2: "Warning", 4: "Critical"}
THERMAL = {0: "Nominal", 1: "Fair", 2: "Serious", 3: "Critical"}
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


class VMStatistics64(C.Structure):
    """Stable rev1 prefix from mach/vm_statistics.h (38 natural_t words).

    Request this revision, not a guessed size for newer macOS structures.
    """
    _fields_ = (
        [(name, C.c_uint32) for name in
         ("free_count", "active_count", "inactive_count", "wire_count")]
        + [(name, C.c_uint64) for name in
           ("zero_fill_count", "reactivations", "pageins", "pageouts", "faults",
            "cow_faults", "lookups", "hits", "purges")]
        + [("purgeable_count", C.c_uint32), ("speculative_count", C.c_uint32)]
        + [(name, C.c_uint64) for name in
           ("decompressions", "compressions", "swapins", "swapouts")]
        + [(name, C.c_uint32) for name in
           ("compressor_page_count", "throttled_count", "external_page_count",
            "internal_page_count")]
        + [("total_uncompressed_pages_in_compressor", C.c_uint64)]
    )


class SwapUsage(C.Structure):
    _fields_ = [("total", C.c_uint64), ("available", C.c_uint64),
                ("used", C.c_uint64), ("pagesize", C.c_uint32),
                ("encrypted", C.c_int32)]


class ThermalReader:
    """Read Apple's public Foundation API without requiring PyObjC or Swift."""

    def __init__(self):
        self.foundation = C.CDLL("/System/Library/Frameworks/Foundation.framework/Foundation")
        self.objc = C.CDLL("/usr/lib/libobjc.A.dylib")
        self.objc.objc_getClass.argtypes = [C.c_char_p]
        self.objc.objc_getClass.restype = C.c_void_p
        self.objc.sel_registerName.argtypes = [C.c_char_p]
        self.objc.sel_registerName.restype = C.c_void_p
        self.send_id = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_void_p)(
            ("objc_msgSend", self.objc))
        self.send_int = C.CFUNCTYPE(C.c_long, C.c_void_p, C.c_void_p)(
            ("objc_msgSend", self.objc))
        self.send_void = C.CFUNCTYPE(None, C.c_void_p, C.c_void_p)(
            ("objc_msgSend", self.objc))
        self.responds = C.CFUNCTYPE(C.c_bool, C.c_void_p, C.c_void_p, C.c_void_p)(
            ("objc_msgSend", self.objc))
        self.select = self.objc.sel_registerName

    def read(self):
        pool = self.send_id(self.objc.objc_getClass(b"NSAutoreleasePool"), self.select(b"new"))
        try:
            info = self.send_id(self.objc.objc_getClass(b"NSProcessInfo"), self.select(b"processInfo"))
            selector = self.select(b"thermalState")
            if not info or not self.responds(info, self.select(b"respondsToSelector:"), selector):
                raise OSError("Foundation thermalState is unavailable")
            return self.send_int(info, selector)
        finally:
            self.send_void(pool, self.select(b"drain"))


class NativeReader:
    def __init__(self):
        if sys.platform != "darwin":
            raise OSError("This monitor requires macOS")
        self.lib = C.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        self.lib.mach_host_self.argtypes = []
        self.lib.mach_host_self.restype = C.c_uint32
        self.host = self.lib.mach_host_self()  # Reuse one send right for the process lifetime.
        for name in ("host_statistics", "host_statistics64"):
            fn = getattr(self.lib, name)
            fn.argtypes = [C.c_uint32, C.c_int, C.c_void_p, C.POINTER(C.c_uint32)]
            fn.restype = C.c_int
        self.lib.host_page_size.argtypes = [C.c_uint32, C.POINTER(C.c_uint32)]
        self.lib.host_page_size.restype = C.c_int
        self.lib.sysctlbyname.argtypes = [C.c_char_p, C.c_void_p,
                                        C.POINTER(C.c_size_t), C.c_void_p, C.c_size_t]
        self.lib.sysctlbyname.restype = C.c_int
        self.thermal = None

    def sysctl(self, name, kind):
        value = kind()
        size = C.c_size_t(C.sizeof(value))
        if self.lib.sysctlbyname(name.encode("ascii"), C.byref(value), C.byref(size), None, 0):
            raise OSError(C.get_errno(), "Cannot read " + name)
        if size.value != C.sizeof(value):
            raise OSError("Unexpected size for " + name)
        return value

    def statistics(self, flavor, value, wide=False):
        count = C.c_uint32(C.sizeof(value) // C.sizeof(C.c_uint32))
        fn = self.lib.host_statistics64 if wide else self.lib.host_statistics
        code = fn(self.host, flavor, C.byref(value), C.byref(count))
        if code or count.value * 4 != C.sizeof(value):
            raise OSError("Mach statistics unavailable (flavor {}, result {})".format(flavor, code))
        return value

    def cpu(self):
        return tuple(self.statistics(3, (C.c_uint32 * 4)()))  # user, system, idle, nice

    def memory(self):
        vm = self.statistics(4, VMStatistics64(), wide=True)
        page = C.c_uint32()
        if self.lib.host_page_size(self.host, C.byref(page)) or page.value == 0:
            raise OSError("Cannot read VM page size")
        return {"compressed_bytes": vm.compressor_page_count * page.value,
                "swapout_pages": vm.swapouts, "page_size": page.value}

    def thermal_state(self):
        if self.thermal is None:
            self.thermal = ThermalReader()
        return self.thermal.read()

    def read(self):
        result = {"errors": {}}
        readers = {
            "cpu_ticks": self.cpu,
            "vm": self.memory,
            "pressure_level": lambda: self.sysctl("kern.memorystatus_vm_pressure_level", C.c_uint32).value,
            "swap_bytes": lambda: self.sysctl("vm.swapusage", SwapUsage).used,
            "physical_bytes": lambda: self.sysctl("hw.memsize", C.c_uint64).value,
            "thermal_level": self.thermal_state,
        }
        for key, reader in readers.items():
            try:
                result[key] = reader()
            except (OSError, AttributeError, ValueError) as exc:
                result[key] = None
                result["errors"][key] = str(exc)
        return result


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
        current["swapout_bytes_per_second"] = None
        vm = current.get("vm")
        old_vm = previous.get("vm") if previous else None
        if (vm and old_vm and vm["page_size"] == old_vm["page_size"]
                and vm["swapout_pages"] >= old_vm["swapout_pages"]):
            current["swapout_bytes_per_second"] = (
                (vm["swapout_pages"] - old_vm["swapout_pages"]) * vm["page_size"] / elapsed)
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


def parse_sensor(text, fan=False):
    lines = text.strip().splitlines()
    if not lines or (not fan and len(lines) != 1) or len(lines) > 16:
        raise ValueError("Missing or unexpected sensor readings")
    values = []
    for line in lines:
        # --value-only promises plain numeric values; do not extract numbers from errors.
        if not re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", line):
            raise ValueError("Non-numeric sensor output")
        value = float(line)
        if not math.isfinite(value) or not (0 <= value <= 20000 if fan else 0 < value <= 150):
            raise ValueError("Sensor reading outside sanity bounds")
        values.append(value)
    return values if fan else values[0]


class SensorSampler:
    def __init__(self, config, runner=run_command, clock=time.monotonic):
        self.enabled = config["enable_istats"]
        self.path = find_istats(config["istats_path"]) if self.enabled else None
        self.interval, self.runner, self.clock = config["sensor_interval"], runner, clock
        self.lock = asyncio.Lock()
        self.cache = {}
        self.next_read = {}
        self.failures = {}

    async def get(self, kind):
        if not self.enabled:
            return {"value": None, "error": "iStats disabled; hardware support unverified"}
        if not self.path:
            return {"value": None, "error": "iStats executable not found; configure istats_path and restart"}
        async with self.lock:
            if self.clock() < self.next_read.get(kind, -1):
                return self.cache[kind]
            args = ["fan", "speed"] if kind == "fan" else ["cpu", "temp"]
            delay = self.interval
            try:
                value = parse_sensor(await self.runner([self.path] + args + ["--value-only"]),
                                     fan=(kind == "fan"))
                result = {"value": value, "error": None}
                self.failures[kind] = 0
            except (OSError, ValueError, asyncio.TimeoutError) as exc:
                # Never serve the old reading as if it were current after an error.
                result = {"value": None, "error": str(exc) or "Sensor command timed out"}
                self.failures[kind] = min(self.failures.get(kind, 0) + 1, 4)
                delay = max(self.interval, min(300, 30 * 2 ** self.failures[kind]))
            self.cache[kind], self.next_read[kind] = result, self.clock() + delay
            return result


def gib(value):
    return "N/A" if value is None else "{:.1f}G".format(value / GIB)


def memory_text(data):
    pressure = PRESSURE.get(data.get("pressure_level"), "N/A")
    swap = gib(data.get("swap_bytes"))
    compressed = gib((data.get("vm") or {}).get("compressed_bytes"))
    rate = data.get("swapout_bytes_per_second")
    out = "N/A" if rate is None else "{:.1f}M/s".format(rate / MIB)
    # Every width retains pressure and swap, the two most useful streaming signals.
    return ["Mem {} | Swap {} | Comp {} | Out {}".format(pressure, swap, compressed, out),
            "Mem {} | Swap {}".format(pressure, swap)]


async def register_components(connection, api, core, sensors, config):
    async def cpu(knobs=None):
        value = core.get()["cpu_percent"]
        return "CPU N/A" if value is None else "CPU {:.0f}%".format(value)

    async def memory(knobs=None):
        return memory_text(core.get())

    async def thermal(knobs=None):
        return "Thermal " + THERMAL.get(core.get().get("thermal_level"), "N/A")

    async def temperature(knobs=None):
        value = (await sensors.get("temperature"))["value"]
        return "Temp N/A" if value is None else "CPU {:.1f}°C".format(value)

    async def fan(knobs=None):
        value = (await sensors.get("fan"))["value"]
        return "Fan N/A" if value is None else "Fan " + "/".join("{:.0f}".format(v) for v in value) + " RPM"

    async def power(knobs=None):
        return "Power N/A"

    entries = [
        ("CPU Usage", "cpu_usage", cpu, "CPU 25%", config["interval"],
         "System CPU busy time, normalized to 0–100% across all cores; first sample is N/A."),
        ("Memory Pressure", "mem_usage", memory, "Mem Normal | Swap 0.0G", config["interval"],
         "Kernel pressure, swap used, compressed RAM (GiB), logical swap-out rate (MiB/s); not Activity Monitor's graph."),
        ("Thermal State", "thermal_state", thermal, "Thermal Nominal", config["interval"],
         "Apple NSProcessInfo thermalState: Nominal/Fair/Serious/Critical; not a temperature or clock measurement."),
        ("CPU Temperature (optional)", "cpu_temperature", temperature, "Temp N/A", config["sensor_interval"],
         "Optional iStats CPU sensor; disabled by default, no Apple Silicon/M6 support guarantee. See --diagnose."),
        ("Fan Speed (optional)", "fan_speed", fan, "Fan N/A", config["sensor_interval"],
         "Optional iStats fan readings; N/A means unknown, including fanless/unsupported hardware. Zero is a valid reading."),
        ("Power (unavailable)", "power_wattage", power, "Power N/A", None,
         "Live power is unavailable. Adapter wattage is not consumption. Use supported powermetrics samplers or a wall meter."),
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
        data["pressure"] = PRESSURE.get(data.get("pressure_level"), "N/A")
        data["thermal"] = THERMAL.get(data.get("thermal_level"), "N/A")
        data["temperature"] = await sensors.get("temperature")
        data["fan"] = await sensors.get("fan")
        data["power"] = {"value": None, "error": "No live power backend"}
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
