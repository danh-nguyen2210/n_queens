import argparse
import csv
import importlib.metadata
import json
import multiprocessing
import platform
from datetime import datetime, timezone
from pathlib import Path

from sat_encoding import ENCODINGS
from sat_solver import solve_sat
from cp_solver import solve_cp_sat, solve_cplex_cp
from ilp_solver import solve_gurobi, solve_cplex_mip
from check_solution import check_result, print_board
from run_limits import run_with_limits


FIELDS = ["N", "Run", "Category", "Encoding", "Solver", "Status", "Valid",
          "Build_Time", "Solve_Time", "Total_Time", "Wall_Time", "Peak_RAM_MB",
          "Num_Variables", "Num_Clauses", "Threads", "Seed", "Message", "Solution"]


def read_args():
    parser = argparse.ArgumentParser(description="So sánh SAT, CP và ILP cho N-Queens")
    parser.add_argument("--sizes", nargs="+", type=int, default=[4, 8, 9, 16, 25, 27, 36, 49, 64, 81, 100, 125, 216, 343, 512, 729, 1000, 1331])
    parser.add_argument("--encodings", nargs="+", choices=ENCODINGS, default=ENCODINGS)
    parser.add_argument("--sat-solvers", nargs="+", default=["glucose3", "cadical195"])
    parser.add_argument("--baselines", nargs="*", choices=["cp-sat", "cplex-cp", "gurobi", "cplex-mip"],
                        default=["cp-sat", "cplex-cp", "gurobi", "cplex-mip"])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=100)
    parser.add_argument("--ram-mb", type=float, default=14336)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    if min(args.sizes) < 1 or args.repeats < 1 or args.timeout <= 0 or args.threads < 1:
        parser.error("N, repeats, timeout và threads phải dương")
    if args.ram_mb < 0 or args.seed < 0 or args.seed + args.repeats - 1 > 2**31 - 1:
        parser.error("ram-mb phải >=0; seed và các seed lặp phải thuộc [0, 2^31-1]")
    return args


def save_environment(folder, args):
    import psutil
    packages = {}
    for name in ["python-sat", "ortools", "docplex", "gurobipy", "cplex", "psutil", "matplotlib"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not installed"
    info = {"utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "os": platform.platform(), "cpu": platform.processor(),
            "logical_cpus": psutil.cpu_count(), "ram_mb": psutil.virtual_memory().total / 1024**2,
            "packages": packages, "arguments": vars(args)}
    (folder / "environment.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    args = read_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = Path(args.output) / stamp
    folder.mkdir(parents=True, exist_ok=False)
    save_environment(folder, args)
    baseline_functions = {"cp-sat": ("CP", solve_cp_sat), "cplex-cp": ("CP", solve_cplex_cp),
                          "gurobi": ("ILP", solve_gurobi), "cplex-mip": ("ILP", solve_cplex_mip)}
    print("Lưu kết quả tại:", folder.resolve())
    with (folder / "runs.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        file.flush()
        for n in args.sizes:
            for run in range(1, args.repeats + 1):
                seed = args.seed + run - 1
                methods = []
                for encoding in args.encodings:
                    for solver in args.sat_solvers:
                        methods.append(("SAT", encoding, solver, solve_sat,
                                        (n, encoding, solver, args.timeout, args.threads, seed)))
                for solver in args.baselines:
                    category, function = baseline_functions[solver]
                    methods.append((category, "", solver, function,
                                    (n, args.timeout, args.threads, seed)))
                for category, encoding, solver, function, values in methods:
                    print(f"N={n}, lần {run}: {encoding} {solver}", flush=True)
                    result = run_with_limits(function, values, args.timeout, args.ram_mb)
                    result = check_result(n, result)
                    row = {"N": n, "Run": run, "Category": category, "Encoding": encoding,
                           "Solver": solver, "Status": result["status"], "Valid": result["valid"],
                           "Build_Time": result["build_time"], "Solve_Time": result["solve_time"],
                           "Total_Time": result["total_time"], "Wall_Time": result["wall_time"],
                           "Peak_RAM_MB": result["peak_ram_mb"], "Num_Variables": result["num_variables"],
                           "Num_Clauses": result["num_clauses"], "Threads": args.threads, "Seed": seed,
                           "Message": result.get("message", ""),
                           "Solution": json.dumps(result["solution"])}
                    if category == "SAT":
                        row["Threads"] = "backend default"
                        row["Seed"] = "backend default"
                    writer.writerow(row)
                    file.flush()
                    print("  ->", result["status"], "| wall:", round(result["wall_time"], 3), "s")
                    if result["solution"] is not None and n <= 8 and result["status"] == "Solved":
                        print_board(result["solution"])
    print("Xong. Dùng analyze_results.py để tổng hợp runs.csv.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()