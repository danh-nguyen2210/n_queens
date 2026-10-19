import time
from run_limits import report_build
from docplex.cp.model import CpoModel
from ortools.sat.python import cp_model


def solve_cp_sat(n, timeout, threads=1, seed=0):
    start = time.perf_counter()
    model = cp_model.CpModel()
    q = [model.NewIntVar(0, n - 1, "q_" + str(i)) for i in range(n)]
    model.AddAllDifferent(q)
    model.AddAllDifferent([q[i] + i for i in range(n)])
    model.AddAllDifferent([q[i] - i for i in range(n)])
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = threads
    solver.parameters.random_seed = seed
    built = time.perf_counter()
    build_time = built - start
    report_build(build_time, n)

    if build_time >= timeout:
        return {
            "status": "Timeout", "solution": None,
            "build_time": build_time, "solve_time": 0.0,
            "total_time": build_time, "num_variables": n, "num_clauses": "",
            "message": "Timeout during model build",
        }

    solver.parameters.max_time_in_seconds = max(0.001, timeout - build_time)
    status = solver.Solve(model)
    end = time.perf_counter()
    result = {
        "status": "Unknown", "solution": None,
        "build_time": build_time, "solve_time": end - built,
        "total_time": end - start, "num_variables": n, "num_clauses": "",
        "message": solver.StatusName(status),
    }
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        result["status"] = "Solved"
        result["solution"] = [int(solver.Value(x)) for x in q]
    elif status == cp_model.INFEASIBLE:
        result["status"] = "Unsat"
    elif status == cp_model.UNKNOWN:
        result["status"] = "Timeout"
    elif status == cp_model.MODEL_INVALID:
        result["status"] = "Error"
    return result


def solve_cplex_cp(n, timeout, threads=1, seed=0):
    start = time.perf_counter()
    model = CpoModel()
    q = model.integer_var_list(n, 0, n - 1, "q")
    model.add(model.all_diff(q))
    model.add(model.all_diff([q[i] + i for i in range(n)]))
    model.add(model.all_diff([q[i] - i for i in range(n)]))
    built = time.perf_counter()
    build_time = built - start
    report_build(build_time, n)

    if build_time >= timeout:
        return {
            "status": "Timeout", "solution": None,
            "build_time": build_time, "solve_time": 0.0,
            "total_time": build_time, "num_variables": n, "num_clauses": "",
            "message": "Timeout during model build",
        }

    answer = model.solve(TimeLimit=max(0.001, timeout - build_time),
                         Workers=threads, RandomSeed=seed, LogVerbosity="Quiet")
    end = time.perf_counter()
    status = str(answer.get_solve_status())
    stop = str(answer.get_stop_cause())
    result = {
        "status": "Unknown", "solution": None,
        "build_time": build_time, "solve_time": end - built,
        "total_time": end - start, "num_variables": n, "num_clauses": "",
        "message": status + "; " + stop,
    }
    if answer.is_solution():
        result["status"] = "Solved"
        result["solution"] = [int(answer.get_value(x)) for x in q]
    elif status == "Infeasible":
        result["status"] = "Unsat"
    elif "timelimit" in stop.lower():
        result["status"] = "Timeout"
    return result