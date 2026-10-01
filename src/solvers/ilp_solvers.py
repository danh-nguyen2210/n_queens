# src/solvers/ilp_solvers.py
import time
import gurobipy as gp
from gurobipy import GRB
from docplex.mp.model import Model as CplexModel
from .base_solver import BaseSolver

class GurobiRunner(BaseSolver):
    """
    Sử dụng Gurobi Optimizer để giải mô hình Integer Linear Programming (ILP).
    Mô hình ILP sử dụng ma trận nhị phân 2 chiều x[i,j].
    """
    def solve(self, timeout: int = 100) -> dict:
        start_time = time.perf_counter()
        try:
            # Tắt output log ra console của Gurobi để không làm rác terminal
            env = gp.Env(empty=True)
            env.setParam("OutputFlag", 0)
            env.start()
            
            model = gp.Model("NQueens_ILP", env=env)
            model.setParam('TimeLimit', timeout)
            
            # x[i,j] = 1 nếu có hậu ở (i,j), ngược lại = 0
            x = model.addVars(self.n, self.n, vtype=GRB.BINARY, name="x")
            
            # Ràng buộc Hàng & Cột: Chính xác 1 quân hậu
            model.addConstrs((x.sum(i, '*') == 1 for i in range(self.n)), name="row")
            model.addConstrs((x.sum('*', j) == 1 for j in range(self.n)), name="col")
            
            # Ràng buộc Đường chéo: Tối đa 1 quân hậu
            for d in range(-self.n + 1, self.n):
                model.addConstr(gp.quicksum(x[i, i - d] for i in range(self.n) if 0 <= i - d < self.n) <= 1)
                
            for d in range(2 * self.n - 1):
                model.addConstr(gp.quicksum(x[i, d - i] for i in range(self.n) if 0 <= d - i < self.n) <= 1)
                
            model.optimize()
            exec_time = time.perf_counter() - start_time
            
            if model.Status == GRB.OPTIMAL:
                solution = [j for i in range(self.n) for j in range(self.n) if x[i, j].X > 0.5]
                return {"status": "Optimal", "time": exec_time, "solution": solution}
            elif model.Status == GRB.TIME_LIMIT:
                return {"status": "Timeout", "time": exec_time}
            else:
                return {"status": "Infeasible", "time": exec_time}
                
        except gp.GurobiError as e:
            return {"status": f"Gurobi Error: {e}", "time": time.perf_counter() - start_time}

class CplexMIPRunner(BaseSolver):
    """
    Sử dụng IBM ILOG CPLEX cho mô hình Mixed Integer Programming (thuần ILP).
    """
    def solve(self, timeout: int = 100) -> dict:
        start_time = time.perf_counter()
        
        model = CplexModel(name="NQueens_MIP")
        model.parameters.timelimit = timeout
        
        # x[i,j] là biến nhị phân
        x = {(i, j): model.binary_var(name=f"x_{i}_{j}") for i in range(self.n) for j in range(self.n)}
        
        # Ràng buộc Hàng & Cột
        for i in range(self.n):
            model.add_constraint(model.sum(x[i, j] for j in range(self.n)) == 1)
        for j in range(self.n):
            model.add_constraint(model.sum(x[i, j] for i in range(self.n)) == 1)
            
        # Ràng buộc Đường chéo
        for d in range(-self.n + 1, self.n):
            model.add_constraint(model.sum(x[i, i - d] for i in range(self.n) if 0 <= i - d < self.n) <= 1)
            
        for d in range(2 * self.n - 1):
            model.add_constraint(model.sum(x[i, d - i] for i in range(self.n) if 0 <= d - i < self.n) <= 1)
            
        # Tắt log Cplex
        model.context.solver.log_output = False
        msol = model.solve()
        
        exec_time = time.perf_counter() - start_time
        
        if msol:
            solution = [j for i in range(self.n) for j in range(self.n) if msol.get_value(x[i, j]) > 0.5]
            return {"status": "Optimal", "time": exec_time, "solution": solution}
        else:
            # Nếu thời gian chạy chạm ngưỡng timeout thì coi như Timeout, ngược lại là Infeasible
            return {"status": "Timeout" if exec_time >= timeout - 0.1 else "Infeasible", "time": exec_time}