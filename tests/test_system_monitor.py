import asyncio
import copy
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "AutoLaunch/system_monitor.py"
spec = importlib.util.spec_from_file_location("monitor", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def snapshot():
    return {"cpu_ticks": (10, 10, 80, 0), "pressure_level": 1,
            "swap_bytes": m.GIB, "physical_bytes": 24 * m.GIB, "thermal_level": 0,
            "vm": {"compressed_bytes": 2 * m.GIB, "swapout_pages": 10,
                   "page_size": 16384}, "errors": {}}


class FakeReader:
    def __init__(self):
        self.data, self.calls = snapshot(), 0

    def read(self):
        self.calls += 1
        return copy.deepcopy(self.data)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.reader = FakeReader()
        self.core = m.CoreSampler(self.reader, clock=lambda: self.now)

    def test_first_sample_and_zero_delta_are_unknown(self):
        self.assertIsNone(self.core.get()["cpu_percent"])
        self.now = 5
        self.assertIsNone(self.core.get()["cpu_percent"])
        self.assertEqual(self.core.get()["swapout_bytes_per_second"], 0)

    def test_cpu_is_system_average_not_process_sum(self):
        self.core.get()
        self.reader.data["cpu_ticks"] = (30, 20, 140, 10)
        self.now = 5
        self.assertAlmostEqual(self.core.get()["cpu_percent"], 40)

    def test_wrap_reset_idle_and_full_busy(self):
        self.assertEqual(m.cpu_percent((2**32 - 5, 0, 0, 0), (5, 0, 0, 0)), 100)
        self.assertIsNone(m.cpu_percent((100, 100, 100, 0), (1, 1, 1, 0)))
        self.assertEqual(m.cpu_percent((0, 0, 0, 0), (0, 0, 100, 0)), 0)

    def test_many_sessions_share_one_sample(self):
        first = self.core.get()
        for _ in range(100):
            self.assertIs(self.core.get(), first)
        self.assertEqual(self.reader.calls, 1)
        self.now = 5
        self.core.get()
        self.assertEqual(self.reader.calls, 2)

    def test_swapout_rate_uses_actual_page_size(self):
        for page_size in (4096, 16384):
            with self.subTest(page_size=page_size):
                reader = FakeReader()
                reader.data["vm"]["page_size"] = page_size
                now = [0]
                core = m.CoreSampler(reader, clock=lambda: now[0])
                core.get()
                now[0] = 10
                reader.data["vm"]["swapout_pages"] += 100
                self.assertEqual(core.get()["swapout_bytes_per_second"], 10 * page_size)

    def test_long_gap_and_counter_reset_reprime_rates(self):
        self.core.get()
        self.now = 500
        self.assertIsNone(self.core.get()["cpu_percent"])
        self.assertIsNone(self.core.get()["swapout_bytes_per_second"])
        self.now = 505
        self.reader.data["vm"]["swapout_pages"] = 0
        self.assertIsNone(self.core.get()["swapout_bytes_per_second"])

    def test_failure_does_not_reuse_old_pressure_or_swap(self):
        self.core.get()
        self.now = 5
        self.reader.data.update(pressure_level=None, swap_bytes=None, vm=None, cpu_ticks=None)
        result = self.core.get()
        self.assertIsNone(result["cpu_percent"])
        self.assertIsNone(result["swapout_bytes_per_second"])
        self.assertIn("Mem N/A | Swap N/A", m.memory_text(result)[0])

    def test_pressure_is_dispatch_values_not_internal_enum_or_free_percent(self):
        for raw, expected in ((1, "Normal"), (2, "Warning"), (4, "Critical"),
                              (0, "N/A"), (3, "N/A"), (99, "N/A"), (None, "N/A")):
            with self.subTest(raw=raw):
                data = snapshot()
                data["pressure_level"] = raw
                self.assertIn("Mem " + expected, m.memory_text(data)[-1])
                self.assertIn("Swap 1.0G", m.memory_text(data)[-1])


class ConfigAndParsingTests(unittest.TestCase):
    def test_defaults_and_invalid_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            self.assertEqual(m.load_config(path), m.DEFAULTS)
            for data in ([], {"interval": 0}, {"interval": True}, {"interval": float("nan")},
                         {"sensor_interval": 1}, {"enable_istats": "false"},
                         {"istats_path": "istats"}, {"unknown": 5}):
                with self.subTest(data=data):
                    path.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        m.load_config(path)

    def test_numeric_readings_zero_fan_and_multiple_fans(self):
        self.assertEqual(m.parse_sensor(" 48.5\n"), 48.5)
        self.assertEqual(m.parse_sensor("0\n2100.5\n", fan=True), [0, 2100.5])

    def test_invalid_sensor_output_is_not_a_measurement(self):
        for text in ("", "\n", "unsupported M6", "Error 42", "NaN", "inf", "0",
                     "-1", "999", "48°C", "48\n49", "\x1b[31m48"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.parse_sensor(text)
        for text in ("", "No fans found", "-5", "20001", "1\n" * 17):
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.parse_sensor(text, fan=True)

    def test_path_discovery_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / "istats"
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o755)
            with patch.object(m.shutil, "which", return_value=str(exe)):
                self.assertEqual(m.find_istats(), str(exe))
                self.assertEqual(m.find_istats(str(exe)), str(exe))
                self.assertIsNone(m.find_istats(str(exe) + "-missing"))
        with patch.object(m.shutil, "which", return_value=None), \
                patch.object(m.os.path, "isfile", side_effect=lambda p: p == "/opt/homebrew/bin/istats"), \
                patch.object(m.os, "access", return_value=True):
            self.assertEqual(m.find_istats(), "/opt/homebrew/bin/istats")


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_iterm2_registration_protocol_when_installed(self):
        try:
            import iterm2
        except ImportError:
            self.skipTest("Run in iTerm2's Python environment to check its API")
        registered = []
        async def subscribe(**kwargs):
            registered.append(kwargs)
            proto = iterm2.api_pb2.RPCRegistrationRequest.StatusBarComponentAttributes()
            kwargs["status_bar_component"].set_fields_in_proto(proto)
            self.assertTrue(proto.unique_identifier.startswith("vxider.iterm-components."))
            self.assertEqual(list(kwargs["arguments"]), ["knobs"])
            return "test-token"
        with patch.object(iterm2.registration, "async_subscribe_to_server_originated_rpc_notification", subscribe):
            await m.register_components(None, iterm2, m.CoreSampler(FakeReader()),
                                        m.SensorSampler(m.DEFAULTS), m.DEFAULTS)
        self.assertEqual(len(registered), 6)
        self.assertEqual(len({r["name"] for r in registered}), 6)

    async def test_disabled_and_missing_backend_never_spawn(self):
        async def forbidden(*args):
            self.fail("Disabled/unavailable sensors must not launch a process")
        for enabled in (False, True):
            config = dict(m.DEFAULTS, enable_istats=enabled)
            with patch.object(m, "find_istats", return_value=None):
                sensors = m.SensorSampler(config, runner=forbidden)
                self.assertIsNone((await sensors.get("fan"))["value"])

    async def test_sensor_cache_shares_work_across_concurrent_sessions(self):
        calls = []
        async def run(argv):
            calls.append(argv)
            await asyncio.sleep(0.01)
            return "0\n2000\n"
        with patch.object(m, "find_istats", return_value="/opt/homebrew/bin/istats"):
            sensors = m.SensorSampler(dict(m.DEFAULTS, enable_istats=True), runner=run)
        results = await asyncio.gather(*(sensors.get("fan") for _ in range(20)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results[0]["value"], [0, 2000])
        self.assertEqual(calls[0][-3:], ["fan", "speed", "--value-only"])

    async def test_error_clears_old_reading_backoff_and_recovery(self):
        now, calls = [0], []
        async def run(argv):
            calls.append(argv)
            if len(calls) in (2, 3):
                raise asyncio.TimeoutError()
            return "52"
        with patch.object(m, "find_istats", return_value="/fake/istats"):
            sensors = m.SensorSampler(dict(m.DEFAULTS, enable_istats=True), runner=run,
                                      clock=lambda: now[0])
        self.assertEqual((await sensors.get("temperature"))["value"], 52)
        now[0] = 30
        self.assertIsNone((await sensors.get("temperature"))["value"])
        now[0] = 89
        await sensors.get("temperature")
        self.assertEqual(len(calls), 2)
        now[0] = 90
        self.assertIsNone((await sensors.get("temperature"))["value"])
        self.assertEqual(sensors.next_read["temperature"], 210)
        now[0] = 210
        self.assertEqual((await sensors.get("temperature"))["value"], 52)
        self.assertEqual(sensors.failures["temperature"], 0)

    async def test_temperature_failure_does_not_hide_valid_fan(self):
        async def run(argv):
            return "unsupported" if "cpu" in argv else "1000"
        with patch.object(m, "find_istats", return_value="/fake/istats"):
            sensors = m.SensorSampler(dict(m.DEFAULTS, enable_istats=True), runner=run)
        self.assertIsNone((await sensors.get("temperature"))["value"])
        self.assertEqual((await sensors.get("fan"))["value"], [1000])

    async def test_subprocess_success_stderr_and_literal_arguments(self):
        text = await m.run_command([sys.executable, "-c",
                                   "import sys; print(sys.argv[1]); print('warning', file=sys.stderr)",
                                   "$(not-a-command); echo nope"])
        self.assertEqual(text.strip(), "$(not-a-command); echo nope")

    async def test_subprocess_nonzero_and_oversized_output(self):
        with self.assertRaises(OSError):
            await m.run_command([sys.executable, "-c", "raise SystemExit(3)"])
        with self.assertRaises(ValueError):
            await asyncio.wait_for(m.run_command(
                [sys.executable, "-c", "print('x' * 1000000)"], limit=1024), timeout=3)

    async def test_timeout_and_cancellation_reap_child(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as folder:
                pid_file = Path(folder) / "pid"
                code = ("import os, pathlib, sys, time; "
                        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)")
                task = asyncio.create_task(m.run_command(
                    [sys.executable, "-c", code, str(pid_file)], timeout=1))
                for _ in range(100):
                    if pid_file.exists():
                        break
                    await asyncio.sleep(0.005)
                self.assertTrue(pid_file.exists())
                pid = int(pid_file.read_text())
                if cancel:
                    task.cancel()
                with self.assertRaises(asyncio.CancelledError if cancel else asyncio.TimeoutError):
                    await task
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)

    async def test_registration_keeps_legacy_ids_and_shared_sampling(self):
        registered = []
        class API:
            StatusBarRPC = staticmethod(lambda f: f)
            class StatusBarComponent:
                def __init__(self, **kwargs):
                    self.options = kwargs
                async def async_register(self, connection, callback, timeout):
                    registered.append((self.options, callback))
        reader = FakeReader()
        await m.register_components(None, API, m.CoreSampler(reader),
                                    m.SensorSampler(m.DEFAULTS), m.DEFAULTS)
        self.assertEqual(len(registered), 6)
        self.assertEqual(len({f.__name__ for _, f in registered}), 6)
        ids = {o["identifier"] for o, _ in registered}
        for suffix in ("mem_usage", "cpu_temperature", "fan_speed", "power_wattage"):
            self.assertIn("vxider.iterm-components." + suffix, ids)
        values = [await f() for _, f in registered]
        self.assertEqual(reader.calls, 1)
        self.assertIn("Thermal Nominal", values)
        self.assertIn("Fan N/A", values)
        self.assertIn("Power N/A", values)


@unittest.skipUnless(sys.platform == "darwin", "Native APIs require macOS")
class NativeTests(unittest.TestCase):
    def test_native_cpu_vm_and_thermal_smoke(self):
        self.assertEqual(C.sizeof(m.VMStatistics64), 152)
        self.assertEqual(C.sizeof(m.SwapUsage), 32)
        data = m.NativeReader().read()
        self.assertEqual(len(data["cpu_ticks"]), 4)
        self.assertIn(data["vm"]["page_size"], (4096, 16384))
        self.assertGreaterEqual(data["vm"]["compressed_bytes"], 0)
        self.assertIn(data["thermal_level"], m.THERMAL)
        # Restricted sandboxes may deny sysctl; denial must stay unknown, never normal.
        for key in ("pressure_level", "swap_bytes", "physical_bytes"):
            if data[key] is None:
                self.assertIn(key, data["errors"])
            else:
                self.assertGreaterEqual(data[key], 0)
        if data["pressure_level"] is not None:
            self.assertIn(data["pressure_level"], m.PRESSURE)


if __name__ == "__main__":
    unittest.main()
