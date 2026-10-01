# src/evaluation/comparator.py
import pandas as pd
from typing import List, Dict

class PerformanceComparator:
    """
    Class chịu trách nhiệm tổng hợp dữ liệu thực nghiệm và đối chiếu hiệu năng chéo
    giữa 3 trường phái: SAT, Constraint Programming (CP) và Integer Linear Programming (ILP).
    Nó giúp xác minh tính đúng đắn (cross-validation) và tìm ra bộ giải vô địch ở từng mức N.
    """
    def __init__(self):
        self.results: List[Dict] = []

    def add_result(self, n: int, category: str, method: str, status: str, time: float, peak_ram_mb: float):
        """
        Thêm một bản ghi thực nghiệm vào danh sách.
        - category: "SAT", "CP", hoặc "ILP"
        - method: Tên tổ hợp (VD: "Binary + Kissat", "CP-SAT", "Gurobi")
        """
        self.results.append({
            "N": n,
            "Category": category,
            "Method": method,
            "Status": status,
            "Time_Seconds": round(time, 4),
            "Peak_RAM_MB": round(peak_ram_mb, 2)
        })

    def get_raw_dataframe(self) -> pd.DataFrame:
        """Trả về toàn bộ dữ liệu dưới dạng DataFrame để xuất ra CSV/Excel."""
        return pd.DataFrame(self.results)

    def cross_validate_correctness(self) -> bool:
        """
        Kiểm tra chéo: Đảm bảo ở cùng một mức N, nếu có bộ giải tìm ra nghiệm (Optimal),
        thì không có bộ giải nào khác báo vô nghiệm (Infeasible).
        Giúp phát hiện lỗi sai trong logic tạo mệnh đề (encodings).
        """
        df = self.get_raw_dataframe()
        is_valid = True
        
        for n, group in df.groupby("N"):
            statuses = group["Status"].unique()
            if "Optimal" in statuses and "Infeasible" in statuses:
                print(f"[CẢNH BÁO LỖI] Ở mức N={n}, có sự mâu thuẫn kết quả (Optimal vs Infeasible) giữa các solvers!")
                is_valid = False
                
        return is_valid

    def generate_summary_report(self):
        df = self.get_raw_dataframe()
        if df.empty:
            return "Chưa có dữ liệu thực nghiệm."

        # 1. Thống kê số lượng theo từng trạng thái
        summary = df.groupby(["N", "Category"]).agg(
            Total_Runs=("Status", "count"),
            Optimal_Count=("Status", lambda s: (s == "Optimal").sum()),
            Timeout_Count=("Status", lambda s: (s == "Timeout").sum()),
            OOM_Count=("Status", lambda s: (s == "OOM").sum()),
            Limit_Count=("Status", lambda s: (s.isin(["License_Limit", "Error"])).sum())
        ).reset_index()

        # 2. Tính trung bình thời gian và RAM chỉ cho các lượt giải thành công (Optimal)
        df_optimal = df[df["Status"] == "Optimal"]
        if not df_optimal.empty:
            perf_stats = df_optimal.groupby(["N", "Category"]).agg(
                Avg_Time_Sec=("Time_Seconds", "mean"),
                Avg_RAM_MB=("RAM_MB", "mean")
            ).reset_index()
            # Làm tròn số liệu
            perf_stats["Avg_Time_Sec"] = perf_stats["Avg_Time_Sec"].round(4)
            perf_stats["Avg_RAM_MB"] = perf_stats["Avg_RAM_MB"].round(2)
            
            summary = summary.merge(perf_stats, on=["N", "Category"], how="left")
        else:
            summary["Avg_Time_Sec"] = None
            summary["Avg_RAM_MB"] = None

        return summary