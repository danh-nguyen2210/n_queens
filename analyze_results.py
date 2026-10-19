import argparse
import csv
import json
import math
import statistics
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path


ENCODING_STYLES = {
    "binomial":   {"color": "#d62728", "marker": "o", "label": "Binomial (Pairwise)"},
    "binary":     {"color": "#ff7f0e", "marker": "s", "label": "Binary"},
    "sequential": {"color": "#2ca02c", "marker": "^", "label": "Sequential Counter"},
    "commander":  {"color": "#1f77b4", "marker": "D", "label": "Commander"},
    "product":    {"color": "#9467bd", "marker": "P", "label": "Product (2-Product)"},
}

BASELINE_STYLES = {
    "cp-sat":    {"color": "#e377c2", "marker": "v", "ls": "-",  "label": "OR-Tools CP-SAT (CP)"},
    "cplex-cp":  {"color": "#17becf", "marker": "*", "ls": "-",  "label": "CPLEX CP Optimizer (CP)"},
    "gurobi":    {"color": "#bcbd22", "marker": "s", "ls": "--", "label": "Gurobi MIP (ILP)"},
    "cplex-mip": {"color": "#7f7f7f", "marker": "d", "ls": "--", "label": "CPLEX MIP (ILP)"},
}

MAJOR_NS = [4, 8, 16, 25, 36, 64, 100, 125, 216, 343, 512, 729, 1000, 1331]


def remove_totalizer_from_dataset(csv_path):
    """Xóa vĩnh viễn các dòng totalizer khỏi runs.csv và environment.json."""
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filtered_rows = [row for row in rows if row.get("Encoding", "").strip().lower() != "totalizer"]
    removed_count = len(rows) - len(filtered_rows)
    if removed_count > 0:
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_rows)
        print(f"Đã xóa {removed_count} dòng 'totalizer' khỏi {csv_path}")

    env_path = csv_path.parent / "environment.json"
    if env_path.exists():
        try:
            env_data = json.loads(env_path.read_text(encoding="utf-8"))
            encs = env_data.get("arguments", {}).get("encodings", [])
            if "totalizer" in encs:
                env_data["arguments"]["encodings"] = [e for e in encs if e != "totalizer"]
                env_path.write_text(json.dumps(env_data, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Đã cập nhật {env_path} (bỏ 'totalizer')")
        except Exception:
            pass


def format_n_axis(ax, all_ns):
    """Hiển thị trực tiếp các mốc kích thước bàn cờ N trên trục log2."""
    ax.set_xscale("log", base=2)
    ticks = [n for n in MAJOR_NS if min(all_ns) <= n <= max(all_ns)]
    ax.set_xticks(ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.tick_params(axis="x", rotation=35, labelsize=8.5)


def amo_counts(k, encoding):
    """Tính chính xác (số biến phụ, số mệnh đề) của 1 ràng buộc AMO độ dài k."""
    if k <= 1:
        return 0, 0
    if encoding == "binomial":
        return 0, k * (k - 1) // 2
    if encoding == "binary":
        b = (k - 1).bit_length()
        return b, k * b
    if encoding == "sequential":
        return k - 1, 3 * k - 4
    if encoding == "commander":
        if k <= 3:
            return 0, k * (k - 1) // 2
        v, c = 0, 0
        num_groups = (k + 2) // 3
        for i in range(0, k, 3):
            g = min(3, k - i)
            v += 1
            c += g * (g - 1) // 2 + g + 1
        rv, rc = amo_counts(num_groups, "commander")
        return v + rv, c + rc
    if encoding == "product":
        if k <= 4:
            return 0, k * (k - 1) // 2
        p = math.isqrt(k)
        if p * p < k:
            p += 1
        q = (k + p - 1) // p
        rv, rc = amo_counts(p, "product")
        cv, cc = amo_counts(q, "product")
        return p + q + rv + cv, 2 * k + rc + cc
    return 0, 0


def exact_nqueens_counts(n, encoding):
    """Tính nhanh tổng số biến và mệnh đề cho bàn cờ N-Queens."""
    total_vars = n * n
    total_clauses = 2 * n
    v, c = amo_counts(n, encoding)
    total_vars += 2 * n * v
    total_clauses += 2 * n * c
    total_vars += 2 * v
    total_clauses += 2 * c
    for k in range(2, n):
        vk, ck = amo_counts(k, encoding)
        total_vars += 4 * vk
        total_clauses += 4 * ck
    return total_vars, total_clauses


def summarize(path):
    remove_totalizer_from_dataset(path)
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    groups = defaultdict(list)
    for row in rows:
        groups[(int(row["N"]), row["Category"], row["Encoding"], row["Solver"])].append(row)
    summary = []
    for (n, category, encoding, solver), runs in sorted(groups.items()):
        counts = Counter(row["Status"] for row in runs)
        solved = [row for row in runs if row["Status"] == "Solved" and row["Valid"] == "True"]
        num_vars = next((int(float(r["Num_Variables"])) for r in runs if r.get("Num_Variables", "") != ""), "")
        num_clauses = next((int(float(r["Num_Clauses"])) for r in runs if r.get("Num_Clauses", "") != ""), "")
        result = {
            "N": n, "Category": category, "Encoding": encoding, "Solver": solver,
            "Num_Variables": num_vars, "Num_Clauses": num_clauses,
            "Runs": len(runs), "Solved": len(solved), "Unsat": counts["Unsat"],
            "Timeout": counts["Timeout"], "MemoryLimit": counts["MemoryLimit"],
            "Other": len(runs) - len(solved) - counts["Unsat"] - counts["Timeout"] - counts["MemoryLimit"],
            "Statuses": "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())),
        }
        for column in ["Build_Time", "Solve_Time", "Total_Time", "Peak_RAM_MB"]:
            values = [float(row[column]) for row in solved if row[column] != ""]
            result["Median_" + column] = ""
            result["Std_" + column] = ""
            if values:
                result["Median_" + column] = statistics.median(values)
                result["Std_" + column] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(result)

    if summary:
        output = path.with_name("summary.csv")
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
        print("Đã lưu bảng tổng hợp:", output)
    return summary


def plot_connected_series(ax, all_ns, n_to_val, color, marker, ls="-", lw=1.8, ms=5.5, label=None):
    """Vẽ đường liền cho các điểm liên tiếp và nối bằng nét chấm mảnh qua các điểm bị Timeout."""
    valid_pts = [(n, max(float(n_to_val[n]), 1e-4)) for n in sorted(all_ns) if n in n_to_val and n_to_val[n] != ""]
    if not valid_pts:
        return
    xs_all = [p[0] for p in valid_pts]
    ys_all = [p[1] for p in valid_pts]

    ax.plot(xs_all, ys_all, color=color, linestyle=":", linewidth=1.0, alpha=0.55)

    xs_seg, ys_seg = [], []
    for n in sorted(all_ns):
        if n in n_to_val and n_to_val[n] != "":
            xs_seg.append(n)
            ys_seg.append(max(float(n_to_val[n]), 1e-4))
        else:
            xs_seg.append(n)
            ys_seg.append(np.nan)
    ax.plot(xs_seg, ys_seg, color=color, marker=marker, linestyle=ls, linewidth=lw, markersize=ms, label=label)


def plot_exp1_complexity(summary, folder):
    """Thí nghiệm 1: Độ phức tạp không gian mô hình của 5 phương pháp SAT Encoding."""
    all_ns = sorted({row["N"] for row in summary})
    emp_vars = defaultdict(dict)
    emp_clauses = defaultdict(dict)

    for row in summary:
        if row["Category"] == "SAT":
            enc, n = row["Encoding"], row["N"]
            if row["Num_Variables"] != "":
                emp_vars[enc][n] = int(row["Num_Variables"])
            if row["Num_Clauses"] != "":
                emp_clauses[enc][n] = int(row["Num_Clauses"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    for enc, style in ENCODING_STYLES.items():
        v_list, c_list = [], []
        for n in all_ns:
            tv, tc = exact_nqueens_counts(n, enc)
            v_list.append(emp_vars[enc].get(n, tv))
            c_list.append(emp_clauses[enc].get(n, tc))

        solved_ns = sorted(emp_vars[enc].keys())
        max_emp_n = max(solved_ns) if solved_ns else 0

        ns_solid = [n for n in all_ns if n <= max_emp_n]
        vs_solid = [v for n, v in zip(all_ns, v_list) if n <= max_emp_n]
        cs_solid = [c for n, c in zip(all_ns, c_list) if n <= max_emp_n]

        ax1.plot(all_ns, v_list, color=style["color"], linestyle="--", linewidth=1.2, alpha=0.55)
        ax2.plot(all_ns, c_list, color=style["color"], linestyle="--", linewidth=1.2, alpha=0.55)

        ax1.plot(ns_solid, vs_solid, color=style["color"], marker=style["marker"],
                 linewidth=1.9, markersize=5.5, label=style["label"])
        ax2.plot(ns_solid, cs_solid, color=style["color"], marker=style["marker"],
                 linewidth=1.9, markersize=5.5, label=style["label"])

    for ax, title, ylabel in [
        (ax1, "(a) Number of CNF Variables vs. Board Size N", "Number of Variables (log scale)"),
        (ax2, "(b) Number of CNF Clauses vs. Board Size N", "Number of Clauses (log scale)"),
    ]:
        format_n_axis(ax, all_ns)
        ax.set_yscale("log")
        ax.set_xlabel("Board Size N", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(True, which="both", linestyle="--", alpha=0.35)
        ax.legend(fontsize=8.5, loc="upper left")

    fig.suptitle("Experiment 1: Structural Complexity of 5 SAT Encodings (Solid = Solved, Dashed = Theoretical)",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = folder / "exp1_encoding_complexity.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Đã xuất:", out)


def plot_exp2_sat_encodings(summary, folder):
    """Thí nghiệm 2: So sánh 5 phương pháp SAT Encoding trên CaDiCaL195 và Glucose3."""
    all_ns = sorted({row["N"] for row in summary})
    solvers = sorted({row["Solver"] for row in summary if row["Category"] == "SAT"})
    if not solvers:
        return

    fig, axes = plt.subplots(1, len(solvers), figsize=(6.7 * len(solvers), 5.2), sharey=True)
    if len(solvers) == 1:
        axes = [axes]

    for ax, solver in zip(axes, solvers):
        for enc, style in ENCODING_STYLES.items():
            n_to_time = {
                row["N"]: row["Median_Total_Time"]
                for row in summary
                if row["Category"] == "SAT" and row["Solver"] == solver and row["Encoding"] == enc
            }
            plot_connected_series(
                ax, all_ns, n_to_time,
                color=style["color"], marker=style["marker"], label=style["label"]
            )
        ax.axhline(100, color="crimson", linestyle=":", linewidth=1.3, label="Timeout Limit (100s)")
        format_n_axis(ax, all_ns)
        ax.set_yscale("log")
        ax.set_xlabel("Board Size N", fontsize=10)
        ax.set_title(f"SAT Solver: {solver}", fontsize=11, fontweight="bold")
        ax.grid(True, which="both", linestyle="--", alpha=0.35)
        ax.legend(fontsize=8.2, loc="upper left")

    axes[0].set_ylabel("Total Runtime: Build + Solve (seconds, log scale)", fontsize=10)
    fig.suptitle("Experiment 2: Runtime Comparison of 5 AMO/ALO Encodings Across SAT Solvers",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = folder / "exp2_sat_encodings_runtime.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Đã xuất:", out)


def plot_exp3_sat_vs_baselines(summary, folder):
    """Thí nghiệm 3: Đối sánh SAT Solving với CP và ILP Baselines."""
    all_ns = sorted({row["N"] for row in summary})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.4))

    sat_picks = [
        ("commander", "cadical195", "#1f77b4", "D", "-",  "SAT: Commander + CaDiCaL195"),
        ("product",   "cadical195", "#9467bd", "P", "-",  "SAT: Product + CaDiCaL195"),
        ("binary",    "cadical195", "#ff7f0e", "s", "-",  "SAT: Binary + CaDiCaL195"),
        ("commander", "glucose3",   "#8c564b", "^", "-.", "SAT: Commander + Glucose3"),
        ("binomial",  "cadical195", "#d62728", "o", "--", "SAT: Binomial + CaDiCaL195"),
    ]

    for enc, solver, color, marker, ls, label in sat_picks:
        n_to_total = {
            r["N"]: r["Median_Total_Time"] for r in summary
            if r["Category"] == "SAT" and r["Encoding"] == enc and r["Solver"] == solver
        }
        n_to_solve = {
            r["N"]: r["Median_Solve_Time"] for r in summary
            if r["Category"] == "SAT" and r["Encoding"] == enc and r["Solver"] == solver
        }
        plot_connected_series(ax1, all_ns, n_to_total, color=color, marker=marker, ls=ls, lw=1.8, label=label)
        plot_connected_series(ax2, all_ns, n_to_solve, color=color, marker=marker, ls=ls, lw=1.8, label=label)

    for solver, style in BASELINE_STYLES.items():
        n_to_total = {r["N"]: r["Median_Total_Time"] for r in summary if r["Solver"] == solver}
        n_to_solve = {r["N"]: r["Median_Solve_Time"] for r in summary if r["Solver"] == solver}
        plot_connected_series(ax1, all_ns, n_to_total, color=style["color"], marker=style["marker"],
                              ls=style["ls"], lw=2.1, ms=6.2, label=style["label"])
        plot_connected_series(ax2, all_ns, n_to_solve, color=style["color"], marker=style["marker"],
                              ls=style["ls"], lw=2.1, ms=6.2, label=style["label"])

    for ax, title, ylabel in [
        (ax1, "(a) End-to-End Total Time (Build + Solve)", "Total Time (seconds, log scale)"),
        (ax2, "(b) Pure Solver Search Time (Solve Only)", "Solve Time (seconds, log scale)"),
    ]:
        ax.axhline(100, color="crimson", linestyle=":", linewidth=1.2)
        format_n_axis(ax, all_ns)
        ax.set_yscale("log")
        ax.set_xlabel("Board Size N", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(True, which="both", linestyle="--", alpha=0.35)
        ax.legend(fontsize=7.8, loc="upper left")

    fig.suptitle("Experiment 3: Paradigm Comparison — SAT Solving vs. CP & ILP Baselines",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = folder / "exp3_sat_vs_baselines.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Đã xuất:", out)


def plot_exp4_memory_and_build(summary, folder):
    """Thí nghiệm 4: Peak RAM và Phân rã Build/Solve Time (5 SAT Encodings + 4 Baselines)."""
    all_ns = sorted({row["N"] for row in summary})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 5.4))

    curves = [
        ("SAT", "binomial",   "cadical195", "#d62728", "o", "-",  "SAT: Binomial (CaDiCaL)"),
        ("SAT", "sequential", "cadical195", "#2ca02c", "^", "-",  "SAT: Sequential (CaDiCaL)"),
        ("SAT", "product",    "cadical195", "#9467bd", "P", "-",  "SAT: Product (CaDiCaL)"),
        ("SAT", "commander",  "cadical195", "#1f77b4", "D", "-",  "SAT: Commander (CaDiCaL)"),
        ("SAT", "binary",     "cadical195", "#ff7f0e", "s", "-",  "SAT: Binary (CaDiCaL)"),
        ("CP",  "",           "cp-sat",     "#e377c2", "v", "--", "CP: OR-Tools CP-SAT"),
        ("CP",  "",           "cplex-cp",   "#17becf", "*", "--", "CP: CPLEX CP"),
        ("ILP", "",           "gurobi",     "#bcbd22", "s", "-.", "ILP: Gurobi MIP"),
        ("ILP", "",           "cplex-mip",  "#7f7f7f", "d", "-.", "ILP: CPLEX MIP"),
    ]
    for cat, enc, solver, color, marker, ls, label in curves:
        n_to_ram = {
            r["N"]: r["Median_Peak_RAM_MB"] for r in summary
            if r["Category"] == cat and r["Encoding"] == enc and r["Solver"] == solver
        }
        plot_connected_series(ax1, all_ns, n_to_ram, color=color, marker=marker, ls=ls, lw=1.8, label=label)

    format_n_axis(ax1, all_ns)
    ax1.set_xlabel("Board Size N", fontsize=10)
    ax1.set_ylabel("Sampled Peak RSS Memory (MB)", fontsize=10)
    ax1.set_title("(a) Memory Footprint Scaling Across Methods", fontsize=11, fontweight="bold")
    ax1.grid(True, which="both", linestyle="--", alpha=0.35)
    ax1.legend(fontsize=8, loc="upper left")

    target_n = 216 if any(r["N"] == 216 and r["Solved"] > 0 for r in summary) else max(all_ns)
    items = []
    for r in summary:
        if r["N"] == target_n and r["Median_Total_Time"] != "":
            if r["Category"] == "SAT" and r["Solver"] != "cadical195":
                continue
            lbl = f"SAT: {r['Encoding']}" if r["Category"] == "SAT" else f"{r['Category']}: {r['Solver']}"
            b_val = float(r["Median_Build_Time"])
            s_val = float(r["Median_Solve_Time"])
            items.append((b_val + s_val, lbl, b_val, s_val))

    items.sort(key=lambda x: x[0])
    bars_labels = [x[1] for x in items]
    build_vals = [x[2] for x in items]
    solve_vals = [x[3] for x in items]

    y_pos = np.arange(len(bars_labels))
    ax2.barh(y_pos, build_vals, color="#4c72b0", label="Model/CNF Build Time (s)")
    ax2.barh(y_pos, solve_vals, left=build_vals, color="#dd8452", label="Solver Search Time (s)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(bars_labels, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Time in Seconds", fontsize=10)
    ax2.set_title(f"(b) Build vs. Solve Breakdown at N = {target_n} (Sorted by Fastest)", fontsize=11, fontweight="bold")
    ax2.grid(True, axis="x", linestyle="--", alpha=0.35)

    max_tot = max((b + s for b, s in zip(build_vals, solve_vals)), default=1.0)
    ax2.set_xlim(0, max_tot * 1.26)
    for idx, (b_val, s_val) in enumerate(zip(build_vals, solve_vals)):
        tot = b_val + s_val
        ax2.text(tot + max_tot * 0.015, idx, f"{tot:.2f}s (B:{b_val:.2f}s)",
                 va="center", ha="left", fontsize=8, color="#222222", fontweight="bold")

    ax2.legend(fontsize=8.5, loc="lower right")

    fig.suptitle("Experiment 4: Memory Consumption and Model Construction Overhead",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = folder / "exp4_memory_and_build.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Đã xuất:", out)


def plot_exp5_cactus_and_heatmap(summary, folder):
    """Thí nghiệm 5: Cactus Plot & Heatmap toàn cục cho 14 phương pháp (5 SAT x 2 + 4 Baselines)."""
    all_ns = sorted({row["N"] for row in summary})
    methods_order = []
    method_times = defaultdict(dict)

    for row in summary:
        label = f"{row['Encoding']} + {row['Solver']}" if row["Category"] == "SAT" else f"{row['Solver']} ({row['Category']})"
        if label not in methods_order:
            methods_order.append(label)
        if row["Median_Total_Time"] != "":
            method_times[label][row["N"]] = float(row["Median_Total_Time"])

    methods_order.sort(key=lambda m: (-len(method_times[m]), sum(method_times[m].values())))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.2), gridspec_kw={"width_ratios": [1.05, 1.35]})

    cmap_lines = plt.cm.tab20(np.linspace(0, 1, len(methods_order)))
    markers = ["o", "s", "^", "D", "v", "P", "X", "*", "d", "<", ">", "p", "h", "8"]
    for idx, m in enumerate(methods_order):
        sorted_t = sorted(method_times[m].values())
        if sorted_t:
            ax1.plot(range(1, len(sorted_t) + 1), sorted_t,
                     color=cmap_lines[idx], marker=markers[idx % len(markers)],
                     linewidth=1.7, markersize=5, label=f"{m} ({len(sorted_t)}/{len(all_ns)})")

    ax1.set_yscale("log")
    ax1.set_xlim(0.5, len(all_ns) + 0.5)
    ax1.set_xticks(range(2, len(all_ns) + 1, 2))
    ax1.set_xlabel("Number of Solved Instances (out of 18 board sizes N)", fontsize=10)
    ax1.set_ylabel("Total Runtime per Instance (seconds, log scale)", fontsize=10)
    ax1.set_title("(a) Cactus Plot: Overall Scalability", fontsize=11, fontweight="bold")
    ax1.grid(True, which="both", linestyle="--", alpha=0.35)
    ax1.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=True)

    matrix = np.full((len(methods_order), len(all_ns)), np.nan)
    for i, m in enumerate(methods_order):
        for j, n in enumerate(all_ns):
            if n in method_times[m]:
                matrix[i, j] = method_times[m][n]

    masked = np.ma.masked_invalid(np.log10(np.maximum(matrix, 1e-3)))
    cmap = plt.cm.YlGnBu.copy()
    cmap.set_bad(color="#f2d7d5")

    im = ax2.imshow(masked, aspect="auto", cmap=cmap)
    ax2.set_xticks(range(len(all_ns)))
    ax2.set_xticklabels([str(n) for n in all_ns], rotation=45, ha="right", fontsize=8.5)
    ax2.set_yticks(range(len(methods_order)))
    ax2.set_yticklabels(methods_order, fontsize=8.5)
    ax2.set_xlabel("Board Size N", fontsize=10)
    ax2.set_title("(b) Runtime Heatmap Across All N (Pink 'TO' = Timeout > 100s)", fontsize=11, fontweight="bold")

    for i in range(len(methods_order)):
        for j in range(len(all_ns)):
            val = matrix[i, j]
            if np.isnan(val):
                ax2.text(j, i, "TO", ha="center", va="center", color="#922b21", fontsize=6.5, fontweight="bold")
            else:
                txt = f"{val:.1f}" if val >= 1.0 else (f"{val:.2f}" if val >= 0.05 else "<0.05")
                text_color = "white" if np.log10(max(val, 1e-3)) > 0.6 else "black"
                ax2.text(j, i, txt, ha="center", va="center", color=text_color, fontsize=6.2)

    cbar = fig.colorbar(im, ax=ax2, fraction=0.035, pad=0.02)
    cbar.set_label("log10(Total Time in seconds)", fontsize=9)

    fig.suptitle("Experiment 5: Holistic Solver Capability Matrix and Cactus Plot",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = folder / "exp5_cactus_and_heatmap.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Đã xuất:", out)


def plot_all_experiments(summary, folder):
    plot_exp1_complexity(summary, folder)
    plot_exp2_sat_encodings(summary, folder)
    plot_exp3_sat_vs_baselines(summary, folder)
    plot_exp4_memory_and_build(summary, folder)
    plot_exp5_cactus_and_heatmap(summary, folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Làm sạch totalizer, tổng hợp kết quả và xuất 5 biểu đồ.")
    parser.add_argument("csv_file", type=Path, nargs="?", default=None)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    csv_path = args.csv_file
    if csv_path is None:
        candidates = sorted(Path("results").glob("*/runs.csv"))
        if not candidates:
            parser.error("Không tìm thấy file runs.csv nào trong thư mục results/")
        csv_path = candidates[-1]
        print("Tự động chọn file mới nhất:", csv_path)

    summary = summarize(csv_path)
    if args.plot:
        plot_all_experiments(summary, csv_path.parent)