import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
import psutil

_ACTIVE_CONN = None


def report_build(build_time, num_variables, num_clauses=""):
    """Gửi thông tin mô hình về tiến trình cha ngay sau khi build xong."""
    if _ACTIVE_CONN is not None:
        try:
            _ACTIVE_CONN.send({
                "build_info": {
                    "build_time": build_time,
                    "num_variables": num_variables,
                    "num_clauses": num_clauses,
                }
            })
        except Exception:
            pass


def error_result(error):
    message = type(error).__name__ + ": " + str(error)
    lower = message.lower()
    status = "Error"
    if isinstance(error, MemoryError):
        status = "MemoryLimit"
    elif isinstance(error, ImportError):
        status = "Unavailable"
    elif type(error).__name__ == "DOcplexLimitsExceeded" or "size-limited license" in lower:
        status = "LicenseLimit"
    elif "license" in lower:
        status = "LicenseError"
    elif "executable" in lower and ("not found" in lower or "not exist" in lower):
        status = "Unavailable"
    return {"status": status, "message": message, "solution": None}


def memory_mb(pid):
    try:
        parent = psutil.Process(pid)
        processes = [parent] + parent.children(recursive=True)
    except psutil.NoSuchProcess:
        return 0.0
    total = 0
    for process in processes:
        try:
            total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / (1024 * 1024)


def worker(function, args, connection):
    global _ACTIVE_CONN
    _ACTIVE_CONN = connection
    pid = os.getpid()
    if sys.platform == "linux":
        # PID trong /proc có thể khác os.getpid() khi chạy trong container.
        pid = int((Path(psutil.PROCFS_PATH) / "self/stat").read_text().split()[0])
    initial_ram = memory_mb(pid)
    connection.send({"monitor_pid": pid, "ram_mb": initial_ram})
    try:
        result = function(*args)
    except Exception as error:
        result = error_result(error)
    result["worker_ram_mb"] = max(initial_ram, memory_mb(pid))
    try:
        connection.send(result)
    finally:
        _ACTIVE_CONN = None
        connection.close()


def stop_process(process, monitor_pid):
    try:
        children = []
        if monitor_pid is not None:
            children = psutil.Process(monitor_pid).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        children = []
    for child in children:
        try:
            child.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if process.is_alive():
        process.terminate()
    process.join(timeout=2)
    if process.is_alive():
        process.kill()
        process.join()


def run_with_limits(function, args, timeout, ram_limit_mb):
    context = mp.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(function, args, send))
    peak = 0.0
    monitor_pid = None
    build_info = {}
    result = None
    start = time.perf_counter()
    worker_start = None
    process.start()
    send.close()
    try:
        while True:
            if monitor_pid is not None:
                peak = max(peak, memory_mb(monitor_pid))
            if ram_limit_mb > 0 and peak > ram_limit_mb:
                result = {"status": "MemoryLimit", "message": "Vượt giới hạn RAM"}
                break
            if receive.poll(0.02):
                while receive.poll(0):
                    try:
                        message = receive.recv()
                    except EOFError:
                        break
                    if "monitor_pid" in message:
                        monitor_pid = message["monitor_pid"]
                        worker_start = time.perf_counter()
                        peak = max(peak, message.get("ram_mb", 0.0))
                    elif "build_info" in message:
                        build_info.update(message["build_info"])
                    else:
                        result = message
                        break
                if result is not None:
                    break
            if not process.is_alive():
                result = {"status": "Error",
                          "message": "Tiến trình dừng, exitcode=" + str(process.exitcode)}
                break
            if time.perf_counter() - start >= timeout :
                result = {"status": "Timeout", "message": "Vượt giới hạn thời gian toàn lượt chạy"}
                break
    finally:
        receive.close()
        stop_process(process, monitor_pid)

    peak = max(peak, result.pop("worker_ram_mb", 0.0))
    result["wall_time"] = time.perf_counter() - start
    result["peak_ram_mb"] = peak
    # Khôi phục thông số build (nếu đã build xong trước khi bị ngắt vì Timeout/MemoryLimit).
    for key, val in build_info.items():
        if result.get(key, "") == "":
            result[key] = val
    for key in ("build_time", "solve_time", "total_time", "num_variables", "num_clauses"):
        result.setdefault(key, "")
    result.setdefault("solution", None)
    return result