import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch


MODULE = Path(__file__).resolve().parents[1] / "AutoLaunch/system_monitor.py"
spec = importlib.util.spec_from_file_location("monitor", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def snapshot():
    return {"cpu_ticks": (10, 10, 80, 0), "errors": {}}


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

    def test_long_gap_reprimes_cpu_baseline(self):
        self.core.get()
        self.now = 500
        self.assertIsNone(self.core.get()["cpu_percent"])
        self.now = 505
        self.reader.data["cpu_ticks"] = (30, 20, 140, 10)
        self.assertAlmostEqual(self.core.get()["cpu_percent"], 40)

    def test_failure_does_not_reuse_old_cpu_reading(self):
        self.core.get()
        self.now = 5
        self.reader.data["cpu_ticks"] = None
        result = self.core.get()
        self.assertIsNone(result["cpu_percent"])
        self.assertEqual(set(result), {"cpu_ticks", "cpu_percent", "errors"})


class ConfigAndParsingTests(unittest.TestCase):
    def test_entrypoint_uses_safe_default_config_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            config = home / 'Library/Application Support/iTerm2/system_monitor.json'
            config.parent.mkdir(parents=True)
            config.write_text('{"interval": 10}')
            script = config.parent / 'Scripts/AutoLaunch/system_monitor.py'
            script.parent.mkdir(parents=True)
            # The obsolete location must not be used by the new default.
            script.with_suffix('.json').write_text('{"unknown": "old configuration"}')
            override = home / 'custom.json'
            override.write_text('{"interval": 15}')
            for extra_args, interval in (([], 10), (['--config', str(override)], 15)):
                with self.subTest(extra_args=extra_args), \
                        patch.object(m.Path, 'home', return_value=home), \
                        patch.object(m, '__file__', str(script)), \
                        patch.object(m.sys, 'argv', ['system_monitor.py', '--diagnose', '--samples', '1'] + extra_args), \
                        patch.object(m, 'diagnose', new_callable=AsyncMock) as diagnose:
                    m.entrypoint()
                    diagnose.assert_awaited_once()
                    self.assertEqual(diagnose.await_args.args[0]['interval'], interval)
                    self.assertEqual(diagnose.await_args.args[1], 1)

    def test_defaults_and_invalid_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            self.assertEqual(m.load_config(path), m.DEFAULTS)
            for data in ([], {"interval": 0}, {"interval": True}, {"interval": float("nan")},
                         {"sensor_interval": 1}, {"enable_istats": "false"},
                         {"istats_path": "istats"}, {"unknown": 5},
                         {"temperature_backend": "auto"}, {"macmon_path": "macmon"},
                         {"temperature_backend": "macmon", "enable_istats": True}):
                with self.subTest(data=data):
                    path.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):
                        m.load_config(path)

    def test_example_enables_macmon_and_defaults_keep_sensors_disabled(self):
        config = m.load_config(MODULE.parent.parent / 'system_monitor.example.json')
        self.assertEqual(config['temperature_backend'], 'macmon')
        self.assertEqual(m.DEFAULTS['temperature_backend'], 'disabled')

    def test_numeric_temperature_reading(self):
        self.assertEqual(m.parse_sensor(" 48.5\n"), 48.5)

    def test_invalid_sensor_output_is_not_a_measurement(self):
        for text in ("", "\n", "unsupported M6", "Error 42", "NaN", "inf", "0",
                     "-1", "999", "48°C", "48\n49", "\x1b[31m48"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.parse_sensor(text)

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

    def test_macmon_path_discovery_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'macmon'
            exe.write_text('#!/bin/sh\nexit 0\n')
            exe.chmod(0o755)
            with patch.object(m.shutil, 'which', return_value=str(exe)):
                self.assertEqual(m.find_macmon(), str(exe))
                self.assertEqual(m.find_macmon(str(exe)), str(exe))
                self.assertIsNone(m.find_macmon(str(exe) + '-missing'))
        with patch.object(m.shutil, 'which', return_value=None), \
                patch.object(m.os.path, 'isfile', side_effect=lambda p: p == '/opt/homebrew/bin/macmon'), \
                patch.object(m.os, 'access', return_value=True):
            self.assertEqual(m.find_macmon(), '/opt/homebrew/bin/macmon')

    def test_macmon_uses_only_cpu_temperature(self):
        data = {'temp': {'cpu_temp_avg': 76.5, 'gpu_temp_avg': 95},
                'memory': {'ram_usage': 10}, 'thermal': 2}
        self.assertEqual(m.parse_macmon_temperature(json.dumps(data)), 76.5)

    def test_macmon_rejects_missing_invalid_or_non_cpu_measurements(self):
        for value in (None, True, '76.5', 0, -1, 151, 10**400, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.parse_macmon_temperature(json.dumps({'temp': {'cpu_temp_avg': value, 'gpu_temp_avg': 50}}))
        for text in ('', '{}', '[]', '{"temp": null}', '{"temp": {"gpu_temp_avg": 50}}',
                     '{"temp": ', '{"temp": {"cpu_temp_avg": 50}}\n{}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.parse_macmon_temperature(text)


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
        self.assertEqual({r["name"] for r in registered},
                         {"system_monitor_cpu_usage", "system_monitor_cpu_temperature"})
        self.assertEqual(len(registered), 2)

    async def test_disabled_and_missing_backend_never_spawn(self):
        async def forbidden(*args, **kwargs):
            self.fail("Disabled/unavailable sensors must not launch a process")
        configs = [m.DEFAULTS, dict(m.DEFAULTS, enable_istats=True),
                   dict(m.DEFAULTS, temperature_backend='macmon')]
        for config in configs:
            with patch.object(m, "find_istats", return_value=None), \
                    patch.object(m, "find_macmon", return_value=None):
                sensors = m.SensorSampler(config, runner=forbidden)
                self.assertIsNone((await sensors.get())["value"])

    async def test_macmon_one_bounded_sample_shared_across_sessions(self):
        calls = []
        async def run(argv, **kwargs):
            calls.append((argv, kwargs))
            await asyncio.sleep(0.01)
            return '{"temp": {"cpu_temp_avg": 76.5}}'
        with patch.object(m, 'find_macmon', return_value='/opt/homebrew/bin/macmon'):
            sensors = m.SensorSampler(dict(m.DEFAULTS, temperature_backend='macmon'), runner=run)
        values = await asyncio.gather(*(sensors.get() for _ in range(20)))
        self.assertEqual([v['value'] for v in values], [76.5] * 20)
        self.assertEqual(calls, [(['/opt/homebrew/bin/macmon', 'pipe', '--samples', '1', '--interval', '100'],
                                  {'timeout': 4, 'limit': 65536})])

    async def test_macmon_missing_cpu_clears_cached_temperature_and_recovers(self):
        now, calls = [0], []
        async def run(argv, **kwargs):
            calls.append(argv)
            value = None if len(calls) == 2 else 74.5
            return json.dumps({'temp': {'cpu_temp_avg': value, 'gpu_temp_avg': 90}})
        with patch.object(m, 'find_macmon', return_value='/opt/homebrew/bin/macmon'):
            sensors = m.SensorSampler(dict(m.DEFAULTS, temperature_backend='macmon'),
                                      runner=run, clock=lambda: now[0])
        self.assertEqual((await sensors.get())['value'], 74.5)
        now[0] = 30
        self.assertIsNone((await sensors.get())['value'])
        now[0] = 89
        self.assertIsNone((await sensors.get())['value'])
        self.assertEqual(len(calls), 2)
        now[0] = 90
        self.assertEqual((await sensors.get())['value'], 74.5)
        self.assertEqual(sensors.failures, 0)

    async def test_command_latency_does_not_skip_next_refresh(self):
        now, calls = [0], []
        async def run(argv, **kwargs):
            calls.append(argv)
            now[0] += 0.8
            return '{"temp": {"cpu_temp_avg": 76.5}}'
        with patch.object(m, 'find_macmon', return_value='/opt/homebrew/bin/macmon'):
            sensors = m.SensorSampler(dict(m.DEFAULTS, temperature_backend='macmon'),
                                      runner=run, clock=lambda: now[0])
        await sensors.get()
        now[0] = 30
        await sensors.get()
        self.assertEqual(len(calls), 2)

    async def test_sensor_cache_shares_work_across_concurrent_sessions(self):
        calls = []
        async def run(argv):
            calls.append(argv)
            await asyncio.sleep(0.01)
            return "48.5\n"
        with patch.object(m, "find_istats", return_value="/opt/homebrew/bin/istats"):
            sensors = m.SensorSampler(dict(m.DEFAULTS, enable_istats=True), runner=run)
        results = await asyncio.gather(*(sensors.get() for _ in range(20)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results[0]["value"], 48.5)
        self.assertEqual(calls[0][-3:], ["cpu", "temp", "--value-only"])

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
        self.assertEqual((await sensors.get())["value"], 52)
        now[0] = 30
        self.assertIsNone((await sensors.get())["value"])
        now[0] = 89
        await sensors.get()
        self.assertEqual(len(calls), 2)
        now[0] = 90
        self.assertIsNone((await sensors.get())["value"])
        self.assertEqual(sensors.next_read, 210)
        now[0] = 210
        self.assertEqual((await sensors.get())["value"], 52)
        self.assertEqual(sensors.failures, 0)

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

    async def test_registration_only_exposes_cpu_usage_and_temperature(self):
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
        self.assertEqual(len(registered), 2)
        self.assertEqual(len({f.__name__ for _, f in registered}), 2)
        ids = {o["identifier"] for o, _ in registered}
        self.assertEqual(ids, {"vxider.iterm-components.cpu_usage", "vxider.iterm-components.cpu_temperature"})
        values = [await f() for _, f in registered]
        self.assertEqual(reader.calls, 1)
        self.assertEqual(values, ["CPU N/A", "Temp N/A"])


@unittest.skipUnless(sys.platform == "darwin", "Native APIs require macOS")
class NativeTests(unittest.TestCase):
    def test_native_cpu_only_smoke(self):
        data = m.NativeReader().read()
        self.assertEqual(set(data), {"cpu_ticks", "errors"})
        self.assertEqual(data["errors"], {})
        self.assertEqual(len(data["cpu_ticks"]), 4)
        self.assertTrue(all(0 <= n < 2**32 for n in data["cpu_ticks"]))


if __name__ == "__main__":
    unittest.main()
