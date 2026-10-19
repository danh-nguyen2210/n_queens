import time
from run_limits import report_build
from docplex.mp.model import Model
import gurobipy as gp
from gurobipy import GRB

def solve_gurobi(n, timeout, threads=1, seed=0):
    
    start = time.perf_counter()
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model("NQueens", env=env) as model:
            model.Params.Threads = threads
            model.Params.Seed = seed
            x = model.addVars(n, n, vtype=GRB.BINARY)
            for i in range(n):
                model.addConstr(gp.quicksum(x[i, j] for j in range(n)) == 1)
            for j in range(n):
                model.addConstr(gp.quicksum(x[i, j] for i in range(n)) == 1)
            for d in range(1 - n, n):
                model.addConstr(gp.quicksum(x[i, i - d] for i in range(n)
                                if 0 <= i - d < n) <= 1)
            for d in range(2 * n - 1):
                model.addConstr(gp.quicksum(x[i, d - i] for i in range(n)
                                if 0 <= d - i < n) <= 1)
            model.update()
            built = time.perf_counter()
            build_time = built - start
            report_build(build_time, n * n)

            if build_time >= timeout:
                return {
                    "status": "Timeout", "solution": None,
                    "build_time": build_time, "solve_time": 0.0,
                    "total_time": build_time, "num_variables": n * n,
                    "num_clauses": "", "message": "Timeout during model build",
                }

            model.Params.TimeLimit = max(0.001, timeout - build_time)
            model.optimize()
            end = time.perf_counter()
            result = {
                "status": "Unknown", "solution": None,
                "build_time": build_time, "solve_time": end - built,
                "total_time": end - start, "num_variables": n * n,
                "num_clauses": "", "message": "Gurobi status=" + str(model.Status),
            }
            if model.SolCount > 0:
                result["status"] = "Solved"
                result["solution"] = [int(j) for i in range(n) for j in range(n)
                                      if x[i, j].X > 0.5]
            elif model.Status == GRB.INFEASIBLE:
                result["status"] = "Unsat"
            elif model.Status == GRB.TIME_LIMIT:
                result["status"] = "Timeout"
            return result


def solve_cplex_mip(n, timeout, threads=1, seed=0):
    start = time.perf_counter()
    model = Model(name="NQueens")
    try:
        model.parameters.threads = threads
        model.parameters.randomseed = seed
        x = {(i, j): model.binary_var(name=f"x_{i}_{j}")
             for i in range(n) for j in range(n)}
        for i in range(n):
            model.add_constraint(model.sum(x[i, j] for j in range(n)) == 1)
        for j in range(n):
            model.add_constraint(model.sum(x[i, j] for i in range(n)) == 1)
        for d in range(1 - n, n):
            model.add_constraint(model.sum(x[i, i - d] for i in range(n)
                                 if 0 <= i - d < n) <= 1)
        for d in range(2 * n - 1):
            model.add_constraint(model.sum(x[i, d - i] for i in range(n)
                                 if 0 <= d - i < n) <= 1)
        built = time.perf_counter()
        build_time = built - start
        report_build(build_time, n * n)

        if build_time >= timeout:
            return {
                "status": "Timeout", "solution": None,
                "build_time": build_time, "solve_time": 0.0,
                "total_time": build_time, "num_variables": n * n,
                "num_clauses": "", "message": "Timeout during model build",
            }

        model.parameters.timelimit = max(0.001, timeout - build_time)
        answer = model.solve(log_output=False)
        end = time.perf_counter()
        status = str(model.solve_details.status)
        result = {
            "status": "Unknown", "solution": None,
            "build_time": build_time, "solve_time": end - built,
            "total_time": end - start, "num_variables": n * n,
            "num_clauses": "", "message": status,
        }
        if answer is not None:
            result["status"] = "Solved"
            result["solution"] = [int(j) for i in range(n) for j in range(n)
                                  if answer.get_value(x[i, j]) > 0.5]
        elif status.lower() in ("infeasible", "integer infeasible"):
            result["status"] = "Unsat"
        elif "time limit" in status.lower():
            result["status"] = "Timeout"
        return result
    finally:
        model.end()