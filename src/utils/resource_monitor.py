# src/utils/resource_monitor.py
import psutil
import time
import os
import signal
from multiprocessing import Process, Event

def monitor_process_memory(pid: int, memory_limit_mb: float, stop_event):
    """
    Theo dõi dung lượng RAM của một tiến trình (và các tiến trình con của nó).
    Nếu vượt quá memory_limit_mb (VD: 14000 MB cho máy 16GB), tự động kill tiến trình.
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    while not stop_event.is_set():
        try:
            # Tính tổng RAM của tiến trình cha và tất cả tiến trình con (do Gurobi/Cplex hay sinh thêm thread)
            total_memory = parent.memory_info().rss
            for child in parent.children(recursive=True):
                total_memory += child.memory_info().rss
                
            total_memory_mb = total_memory / (1024 * 1024)
            
            if total_memory_mb > memory_limit_mb:
                print(f"\n[OOM ALERT] Tiến trình {pid} ngốn {total_memory_mb:.2f} MB RAM. Đang tiêu diệt để bảo vệ hệ thống!")
                # Kill toàn bộ tree
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                break
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
            
        time.sleep(0.1)

def get_max_memory_usage(pid: int) -> float:
    """Hàm phụ trợ lấy dung lượng RAM hiện tại (dùng để ghi log Peak RAM nếu chạy xong an toàn)"""
    try:
        process = psutil.Process(pid)
        return process.memory_info().rss / (1024 * 1024)
    except:
        return 0.0