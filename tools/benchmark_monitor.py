#!/usr/bin/env python3
"""Measure the core sampler in this process; excludes iTerm2 UI and optional sensors."""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import statistics
import time

spec = importlib.util.spec_from_file_location(
    "monitor", Path(__file__).resolve().parents[1] / "AutoLaunch/system_monitor.py")
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if not 2 <= args.samples <= 720:
        parser.error("--samples must be between 2 and 720")
    core = monitor.CoreSampler(monitor.NativeReader())
    core.get()  # Exclude interpreter/framework startup.
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    times = []
    errors = {}
    for _ in range(args.samples):
        time.sleep(5)
        start = time.perf_counter()
        result = core.get()
        times.append((time.perf_counter() - start) * 1000)
        errors.update(result["errors"])
    cpu_seconds = time.process_time() - cpu_start
    wall_seconds = time.perf_counter() - wall_start
    print(json.dumps({"samples": args.samples, "wall_seconds": wall_seconds,
                      "process_cpu_seconds": cpu_seconds,
                      "process_cpu_percent_one_core": 100 * cpu_seconds / wall_seconds,
                      "sample_median_ms": statistics.median(times), "sample_max_ms": max(times),
                      "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / monitor.MIB,
                      "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
