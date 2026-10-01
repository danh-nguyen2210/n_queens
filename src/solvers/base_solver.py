# src/solvers/base_solver.py
from abc import ABC, abstractmethod
import time

class BaseSolver(ABC):
    """
    Interface chung cho tất cả các bộ giải (SAT, CP, ILP).
    Đảm bảo đầu ra đồng nhất để main_experiment.py dễ dàng ghi log.
    """
    def __init__(self, n: int):
        self.n = n

    @abstractmethod
    def solve(self, timeout: int = 100) -> dict:
        """
        Thực thi quá trình giải.
        Trả về dictionary chuẩn: {"status": "Optimal" / "Infeasible" / "Timeout", "time": float}
        """
        pass