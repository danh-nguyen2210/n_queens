# src/utils/wandb_logger.py
import wandb
from typing import Dict, Any

class ExperimentLogger:
    """
    Tích hợp Weights & Biases để tự động thu thập và vẽ biểu đồ thực nghiệm.
    """
    def __init__(self, project_name: str = "NQueens-SAT-CP-ILP"):
        # Yêu cầu bạn đã chạy `wandb login` trên terminal
        wandb.init(project=project_name, entity=None)
        
        # Định nghĩa các metric để vẽ bảng
        wandb.define_metric("N_size")
        wandb.define_metric("Execution_Time", step_metric="N_size")
        wandb.define_metric("Peak_RAM", step_metric="N_size")

    def log_run(self, n: int, category: str, method: str, status: str, time_sec: float, ram_mb: float):
        """Ghi nhận 1 lượt chạy vào hệ thống W&B"""
        log_data = {
            "N_size": n,
            "Category": category,
            "Method": method,
            "Status": status,
            "Execution_Time": time_sec,
            "Peak_RAM": ram_mb
        }
        wandb.log(log_data)
        
    def finish(self):
        wandb.finish()