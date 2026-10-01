# src/solvers/sat_solvers.py
import time
from pysat.solvers import Solver
from .base_solver import BaseSolver

class SATRunner(BaseSolver):
    """
    Nhận tập mệnh đề CNF từ thư mục encodings và gọi các solver của thư viện PySAT.
    """
    def __init__(self, n: int, solver_name: str, clauses: list[list[int]]):
        super().__init__(n)
        self.solver_name = solver_name
        self.clauses = clauses

    def solve(self, timeout: int = 100) -> dict:
        start_time = time.perf_counter()
        try:
            with Solver(name=self.solver_name, bootstrap_with=self.clauses) as solver:
                is_sat = solver.solve()
                exec_time = time.perf_counter() - start_time
                
                if is_sat:
                    # Trích xuất N^2 biến đầu tiên để tạo thành mảng 1 chiều chứa 0 và 1
                    model = solver.get_model()
                    board = [1 if v > 0 else 0 for v in model[:self.n**2]]
                    return {"status": "Optimal", "time": exec_time, "solution": board}
                else:
                    return {"status": "Infeasible", "time": exec_time}
                    
        except Exception as e:
            return {"status": f"Error: {str(e)}", "time": time.perf_counter() - start_time}