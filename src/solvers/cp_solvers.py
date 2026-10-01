# src/solvers/cp_solvers.py
import time
from ortools.sat.python import cp_model
from docplex.cp.model import CpoModel
from .base_solver import BaseSolver

class CPSatRunner(BaseSolver):
    """
    Sử dụng Constraint Programming của Google OR-Tools (CP-SAT).
    Mô hình CP tối ưu bằng cách dùng 1 mảng 1 chiều thay vì ma trận 2 chiều.
    """
    def solve(self, timeout: int = 100) -> dict:
        start_time = time.perf_counter()
        model = cp_model.CpModel()
        
        # q[i] = j nghĩa là có quân hậu ở hàng i, cột j
        q = [model.NewIntVar(0, self.n - 1, f'q_{i}') for i in range(self.n)]
        
        # Ràng buộc: Không có 2 quân hậu cùng cột
        model.AddAllDifferent(q)
        
        # Ràng buộc: Không có 2 quân hậu cùng đường chéo chính (\) và phụ (/)
        model.AddAllDifferent([q[i] + i for i in range(self.n)])
        model.AddAllDifferent([q[i] - i for i in range(self.n)])
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = timeout
        status = solver.Solve(model)
        
        exec_time = time.perf_counter() - start_time
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            solution = [solver.Value(q[i]) for i in range(self.n)]
            return {"status": "Optimal", "time": exec_time, "solution": solution}
        elif status == cp_model.UNKNOWN:
            return {"status": "Timeout", "time": exec_time}
        else:
            return {"status": "Infeasible", "time": exec_time}

class CplexCPRunner(BaseSolver):
    """
    Sử dụng IBM ILOG CPLEX CP Optimizer.
    Yêu cầu đã cài đặt thư viện docplex và IBM CPLEX Studio.
    """
    def solve(self, timeout: int = 100) -> dict:
        start_time = time.perf_counter()
        mdl = CpoModel(name='NQueens_CP')
        
        q = mdl.integer_var_list(self.n, 0, self.n - 1, "q")
        
        mdl.add(mdl.all_diff(q))
        mdl.add(mdl.all_diff([q[i] + i for i in range(self.n)]))
        mdl.add(mdl.all_diff([q[i] - i for i in range(self.n)]))
        
        # Đặt TimeLimit cho Cplex CP
        msol = mdl.solve(TimeLimit=timeout, LogVerbosity='Quiet')
        
        exec_time = time.perf_counter() - start_time
        
        if msol and msol.is_solution():
            solution = [msol.get_value(q[i]) for i in range(self.n)]
            return {"status": "Optimal", "time": exec_time, "solution": solution}
        else:
            return {"status": "Timeout" if exec_time >= timeout else "Infeasible", "time": exec_time}