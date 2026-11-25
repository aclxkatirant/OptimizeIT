#!/usr/bin/env python3
"""OptimizeIT measurement tool.

Runs a command repeatedly and records wall time, CPU time and peak memory,
then compares two measurements.

Usage:
    python measure.py run --name before --runs 10 --warmup 2 \
        --output .optimizeit/before.json -- <command> [args...]
    python measure.py compare .optimizeit/before.json .optimizeit/after.json

Options for `run`:
    --cwd DIR          working directory for the command
    --timeout SECONDS  kill a run that takes longer than this
    --shell            run the command through the shell (pipes, &&, env syntax)
    --allow-failure    keep measuring even if the command exits non-zero
    --show-output      do not silence the command's stdout

Peak memory is measured for the direct child process. On Linux/macOS the
figure also covers descendants the child waited for; on Windows it covers the
direct child only. Measure the underlying command (e.g. `node bench.js`, not
`npm run bench`) when memory matters.

Standard library only. Python 3.8+.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time

TOOL_ID = "optimizeit-measure"
FORMAT_VERSION = 1
IS_WINDOWS = os.name == "nt"


# --------------------------------------------------------------------------- #
# Process resource usage
# --------------------------------------------------------------------------- #

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    _psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    _kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    _kernel32.GetProcessTimes.restype = wintypes.BOOL

    def _filetime_seconds(ft):
        return ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 10_000_000.0

    def _windows_usage(proc):
        """Return (peak_rss_bytes, cpu_seconds) for a finished Popen on Windows."""
        handle = int(proc._handle)  # handle stays valid until the Popen object is collected
        peak = None
        cpu = None
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        if _psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            peak = int(counters.PeakWorkingSetSize)
        creation, exit_, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if _kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_),
                                     ctypes.byref(kernel), ctypes.byref(user)):
            cpu = _filetime_seconds(kernel) + _filetime_seconds(user)
        return peak, cpu


def _exit_code_from_status(status):
    if hasattr(os, "waitstatus_to_exitcode"):
        return os.waitstatus_to_exitcode(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    return os.WEXITSTATUS(status)


def run_once(command, cwd, shell, timeout, show_output):
    """Run the command once. Returns a dict with wall_s, cpu_s, peak_rss_bytes, exit_code, stderr_tail."""
    stderr_file = tempfile.TemporaryFile()
    stdout = None if show_output else subprocess.DEVNULL
    timed_out = {"value": False}

    start = time.perf_counter()
    proc = subprocess.Popen(command, cwd=cwd, shell=shell, stdout=stdout, stderr=stderr_file,
                            stdin=subprocess.DEVNULL)

    def _kill():
        timed_out["value"] = True
        try:
            proc.kill()
        except OSError:
            pass

    timer = threading.Timer(timeout, _kill) if timeout else None
    if timer:
        timer.start()

    peak = None
    cpu = None
    try:
        if IS_WINDOWS:
            proc.wait()
            wall = time.perf_counter() - start
            peak, cpu = _windows_usage(proc)
            exit_code = proc.returncode
        else:
            _, status, usage = os.wait4(proc.pid, 0)
            wall = time.perf_counter() - start
            exit_code = _exit_code_from_status(status)
            proc.returncode = exit_code  # we reaped it ourselves
            cpu = usage.ru_utime + usage.ru_stime
            # ru_maxrss: kilobytes on Linux, bytes on macOS
            peak = usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024
    finally:
        if timer:
            timer.cancel()

    stderr_file.seek(0, os.SEEK_END)
    size = stderr_file.tell()
    stderr_file.seek(max(0, size - 4000))
    tail = stderr_file.read().decode("utf-8", errors="replace")
    stderr_file.close()

    return {
        "wall_s": wall,
        "cpu_s": cpu,
        "peak_rss_bytes": peak,
        "exit_code": exit_code,
        "timed_out": timed_out["value"],
        "stderr_tail": tail,
    }


# --------------------------------------------------------------------------- #
# Statistics and formatting
# --------------------------------------------------------------------------- #

def summarize(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": statistics.fmean(ordered) if hasattr(statistics, "fmean") else statistics.mean(ordered),
        "median": statistics.median(ordered),
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
        "p95": ordered[p95_index],
    }


def fmt_seconds(value):
    if value is None:
        return "n/a"
    if value < 1e-3:
        return "%.1f µs" % (value * 1e6)
    if value < 1:
        return "%.1f ms" % (value * 1e3)
    return "%.3f s" % value


def fmt_bytes(value):
    if value is None:
        return "n/a"
    for unit, size in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if value >= size:
            return "%.1f %s" % (value / size, unit)
    return "%d B" % value


METRICS = [
    ("wall_s", "Wall time", fmt_seconds),
    ("cpu_s", "CPU time", fmt_seconds),
    ("peak_rss_bytes", "Peak memory (RSS)", fmt_bytes),
]

# Smallest absolute change treated as meaningful (below this, differences are
# dominated by timer resolution or allocator noise).
MIN_ABS_CHANGE = {"wall_s": 0.001, "cpu_s": 0.016, "peak_rss_bytes": 1 << 20}


def environment():
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        # identifies "same machine" without storing the host name
        "hostname_hash": hashlib.sha256(platform.node().encode("utf-8")).hexdigest()[:12],
    }


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_run(args, command):
    if not command:
        print("error: no command given. Put the command after `--`.", file=sys.stderr)
        return 2
    if args.runs < 1 or args.warmup < 0:
        print("error: --runs must be >= 1 and --warmup >= 0", file=sys.stderr)
        return 2
    run_command = " ".join(command) if args.shell else command
    cwd = os.path.abspath(args.cwd) if args.cwd else os.getcwd()

    def execute(label, index, total):
        result = run_once(run_command, cwd, args.shell, args.timeout, args.show_output)
        status = "ok" if result["exit_code"] == 0 else "exit %s" % result["exit_code"]
        if result["timed_out"]:
            status = "TIMEOUT"
        print("  %s %d/%d: %s, %s, %s" % (label, index, total, fmt_seconds(result["wall_s"]),
                                           fmt_bytes(result["peak_rss_bytes"]), status), file=sys.stderr)
        if (result["exit_code"] != 0 or result["timed_out"]) and not args.allow_failure:
            print("\nerror: the command failed; a failing command is not a valid benchmark.", file=sys.stderr)
            if result["stderr_tail"].strip():
                print("stderr (tail):\n" + result["stderr_tail"], file=sys.stderr)
            print("Fix the command, or pass --allow-failure if a non-zero exit is expected.", file=sys.stderr)
            return None
        return result

    print("Measuring %r (%d warm-up, %d runs) in %s" % (run_command, args.warmup, args.runs, cwd), file=sys.stderr)
    for i in range(args.warmup):
        if execute("warm-up", i + 1, args.warmup) is None:
            return 1
    results = []
    for i in range(args.runs):
        result = execute("run", i + 1, args.runs)
        if result is None:
            return 1
        result.pop("stderr_tail", None)
        results.append(result)

    summary = {key: summarize([r[key] for r in results]) for key, _, _ in METRICS}
    data = {
        "tool": TOOL_ID,
        "format_version": FORMAT_VERSION,
        "name": args.name,
        "command": command,
        "shell": args.shell,
        "cwd": cwd,
        "warmup": args.warmup,
        "runs": args.runs,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "environment": environment(),
        "memory_scope": "direct child only" if IS_WINDOWS else "child and waited-for descendants",
        "results": results,
        "summary": summary,
    }

    print("\n| Metric | Median | Mean | Stdev | Min | p95 |")
    print("|---|---:|---:|---:|---:|---:|")
    for key, label, fmt in METRICS:
        s = summary[key]
        if s:
            print("| %s | %s | %s | %s | %s | %s |" % (label, fmt(s["median"]), fmt(s["mean"]),
                                                    fmt(s["stdev"]), fmt(s["min"]), fmt(s["p95"])))
        else:
            print("| %s | not measured | | | | |" % label)

    if args.output:
        directory = os.path.dirname(os.path.abspath(args.output))
        os.makedirs(directory, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("\nSaved: %s" % args.output)
    return 0


def load_measurement(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("tool") != TOOL_ID:
        raise ValueError("%s is not an OptimizeIT measurement file" % path)
    return data


def cmd_compare(args):
    try:
        before = load_measurement(args.before)
        after = load_measurement(args.after)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    warnings = []
    if before["command"] != after["command"] or before.get("cwd") != after.get("cwd"):
        warnings.append("The two measurements used different commands or working directories; "
                        "they are not directly comparable.")
    env_b, env_a = before.get("environment", {}), after.get("environment", {})
    for key in ("platform", "machine", "cpu_count", "hostname_hash"):
        if env_b.get(key) != env_a.get(key):
            warnings.append("Environment differs (%s): %s vs %s." % (key, env_b.get(key), env_a.get(key)))
            break
    if min(before["runs"], after["runs"]) < 5:
        warnings.append("Fewer than 5 runs in at least one measurement; significance is unreliable.")

    print("## Performance Comparison: %s → %s" % (before["name"], after["name"]))
    print("")
    print("Command: `%s`" % " ".join(after["command"]))
    print("Runs: %d (before) / %d (after), warm-up %d / %d" % (before["runs"], after["runs"],
                                                               before["warmup"], after["warmup"]))
    print("")
    print("| Metric | Before (median) | After (median) | Change | Significant? |")
    print("|---|---:|---:|---:|---|")
    for key, label, fmt in METRICS:
        b = before["summary"].get(key)
        a = after["summary"].get(key)
        if not b or not a:
            print("| %s | %s | %s | — | not measured |" % (label, fmt(b["median"]) if b else "not measured",
                                                          fmt(a["median"]) if a else "not measured"))
            continue
        diff = a["median"] - b["median"]
        change = (diff / b["median"] * 100.0) if b["median"] else float("nan")
        noise = math.sqrt(b["stdev"] ** 2 + a["stdev"] ** 2)
        if min(b["n"], a["n"]) < 3:
            verdict = "insufficient runs"
        elif abs(diff) > 2 * noise and abs(change) >= 1.0 and abs(diff) >= MIN_ABS_CHANGE[key]:
            verdict = "yes (improvement)" if diff < 0 else "yes (REGRESSION)"
        else:
            verdict = "no (within noise)"
        print("| %s | %s | %s | %+.1f%% | %s |" % (label, fmt(b["median"]), fmt(a["median"]), change, verdict))

    print("")
    print("Significance rule: |Δ median| > 2 × √(σ_before² + σ_after²), |change| ≥ 1%, "
          "and |Δ| ≥ 1 ms (wall) / 16 ms (CPU) / 1 MB (memory).")
    if warnings:
        print("")
        for w in warnings:
            print("> WARNING: %s" % w)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        split = argv.index("--")
        argv, command = argv[:split], argv[split + 1:]

    parser = argparse.ArgumentParser(description="OptimizeIT measurement tool")
    sub = parser.add_subparsers(dest="action")

    run = sub.add_parser("run", help="measure a command (put the command after --)")
    run.add_argument("--name", default="measurement", help="label for this measurement (e.g. before, after)")
    run.add_argument("--runs", type=int, default=10, help="measured runs (default 10)")
    run.add_argument("--warmup", type=int, default=2, help="unmeasured warm-up runs (default 2)")
    run.add_argument("--output", help="write results as JSON to this file")
    run.add_argument("--cwd", help="working directory for the command")
    run.add_argument("--timeout", type=float, help="per-run timeout in seconds")
    run.add_argument("--shell", action="store_true", help="run through the shell")
    run.add_argument("--allow-failure", action="store_true", help="do not abort on non-zero exit codes")
    run.add_argument("--show-output", action="store_true", help="show the command's stdout")

    compare = sub.add_parser("compare", help="compare two measurement files")
    compare.add_argument("before")
    compare.add_argument("after")

    args = parser.parse_args(argv)
    if args.action == "run":
        return cmd_run(args, command)
    if args.action == "compare":
        return cmd_compare(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main())
