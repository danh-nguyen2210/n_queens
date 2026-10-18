import time
from sat_encoding import NQueensEncoder
from run_limits import report_build
from pysat.solvers import Solver
from pysat.solvers import SolverNames


def resolve_solver_name(name):
    if not name.startswith("cadical"):
        return name
    for candidate in [name, "cadical195", "cadical153", "cadical103", "cadical"]:
        for attr in dir(SolverNames):
            val = getattr(SolverNames, attr)
            if isinstance(val, (list, tuple)) and candidate in val:
                return candidate
    return name


def solve_sat(n, encoding, solver_name, timeout, threads=1, seed=0):
    actual_name = resolve_solver_name(solver_name)
    start = time.perf_counter()
    encoder = NQueensEncoder(n, encoding)
    clauses = encoder.build()
    with Solver(name=actual_name, bootstrap_with=clauses) as solver:
        built = time.perf_counter()
        build_time = built - start
        num_vars = solver.nof_vars()
        num_clauses = len(clauses)
        # Gửi ngay thông số mô hình về tiến trình cha trước khi giải
        report_build(build_time, num_vars, num_clauses)

        if build_time >= timeout:
            return {
                "status": "Timeout", "solution": None,
                "build_time": build_time, "solve_time": 0.0,
                "total_time": build_time,
                "num_variables": num_vars, "num_clauses": num_clauses,
                "message": "Vượt giới hạn thời gian khi xây dựng CNF",
            }

        sat = solver.solve()
        end = time.perf_counter()
        result = {
            "status": "Unsat", "solution": None,
            "build_time": build_time, "solve_time": end - built,
            "total_time": end - start,
            "num_variables": num_vars, "num_clauses": num_clauses,
            "message": "" if actual_name == solver_name else f"Dùng {actual_name}",
        }
        if sat:
            positive = set(v for v in solver.get_model() if v > 0)
            queens = []
            for row in range(n):
                columns = [col for col in range(n) if encoder.var(row, col) in positive]
                if len(columns) != 1:
                    result["status"] = "Invalid"
                    result["message"] = "Mỗi hàng phải có đúng một quân hậu"
                    return result
                queens.append(int(columns[0]))
            result["status"] = "Solved"
            result["solution"] = queens
        return result