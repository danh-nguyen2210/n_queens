# src/main_experiment.py
import time
import multiprocessing
from multiprocessing import Process, Queue, Event

# Import toàn bộ các module đã thiết kế
from sat_encodings.binomial import BinomialEncoder
from sat_encodings.binary import BinaryEncoder
from sat_encodings.commander import CommanderEncoder
from sat_encodings.product import ProductEncoder
from sat_encodings.sequential_counter import SequentialCounterEncoder
from sat_encodings.totalizer import TotalizerEncoder

from solvers.sat_solvers import SATRunner
from solvers.cp_solvers import CPSatRunner, CplexCPRunner
from solvers.ilp_solvers import GurobiRunner, CplexMIPRunner

from evaluation.comparator import PerformanceComparator
from utils.resource_monitor import monitor_process_memory, get_max_memory_usage
from utils.wandb_logger import ExperimentLogger

# CẤU HÌNH THỰC NGHIỆM
TIMEOUT_SECONDS = 100       # Giới hạn 100 giây như tài liệu khóa trước
MEMORY_LIMIT_MB = 14000     # Giới hạn 14GB RAM cho máy 16GB
#N_SIZES = [8, 16, 32, 64, 100]
N_SIZES = [100]

def print_board(n: int, solution: list, solver_type: str):
    """Vẽ bàn cờ ra terminal để kiểm chứng trực quan"""
    print("  " + "-" * (n * 2 - 1))
    if solver_type == "SAT":
        for i in range(n):
            row = solution[i*n : (i+1)*n]
            print("  " + " ".join(["Q" if x == 1 else "." for x in row]))
    elif solver_type == "CP":
        for i in range(n):
            row = ["Q" if j == solution[i] else "." for j in range(n)]
            print("  " + " ".join(row))
    print("  " + "-" * (n * 2 - 1))

def solver_worker(solver_instance, result_queue: Queue):
    """Hàm chạy trong tiến trình con. Giải và đẩy kết quả vào hàng đợi."""
    res = solver_instance.solve(timeout=TIMEOUT_SECONDS)
    result_queue.put(res)

def execute_with_limits(solver_instance, method_name: str) -> dict:
    """
    Bọc quá trình chạy solver bằng Multiprocessing để kiểm soát Timeout và OOM.
    """
    q = Queue()
    p = Process(target=solver_worker, args=(solver_instance, q))
    p.start()
    
    # Khởi động luồng giám sát RAM
    stop_event = Event()
    monitor_p = Process(target=monitor_process_memory, args=(p.pid, MEMORY_LIMIT_MB, stop_event))
    monitor_p.start()
    
    peak_ram = 0.0
    start_wait = time.time()
    
    result = {"status": "Unknown", "time": TIMEOUT_SECONDS}
    
    while p.is_alive():
        current_ram = get_max_memory_usage(p.pid)
        if current_ram > peak_ram:
            peak_ram = current_ram
            
        # Kiểm tra Timeout thủ công để kill tiến trình C/C++ cứng đầu
        if time.time() - start_wait > TIMEOUT_SECONDS:
            print(f"[{method_name}] Timeout! Đang đóng băng tiến trình...")
            p.terminate()
            p.join()
            result = {"status": "Timeout", "time": TIMEOUT_SECONDS}
            break
            
        time.sleep(0.1)
        
    stop_event.set()
    monitor_p.join()
    
    # Nếu process kết thúc bình thường và queue có dữ liệu
    if not q.empty() and result["status"] == "Unknown":
        result = q.get()
    elif result["status"] == "Unknown":
        # Process bị kill do OOM (luồng monitor đã ra tay)
        result = {"status": "OOM", "time": time.time() - start_wait}
        
    result["peak_ram_mb"] = peak_ram
    return result

if __name__ == "__main__":
    # Fix lỗi multiprocessing trên Windows
    multiprocessing.freeze_support()
    
    logger = ExperimentLogger()
    comparator = PerformanceComparator()
    
    # Danh sách các SAT Solver trong thư viện PySAT
    sat_solver_names = ['glucose3']
    
    for n in N_SIZES:
        print(f"\n{'='*50}\nBẮT ĐẦU THỰC NGHIỆM VỚI BÀN CỜ N = {n}\n{'='*50}")
        
        # 1. TRƯỜNG PHÁI SAT SOLVING
        encoders = {
            "Binomial": BinomialEncoder(n),
            "Binary": BinaryEncoder(n),
            "Commander": CommanderEncoder(n),
            "Product": ProductEncoder(n),
            "Sequential": SequentialCounterEncoder(n),
            "Totalizer": TotalizerEncoder(n)
        }
        
        for enc_name, encoder in encoders.items():
            print(f"\nĐang sinh clauses cho {enc_name} (N={n})...")
            # Nếu sinh clauses bị tràn RAM (ví dụ Binomial N=100), 
            # có thể cần try-except ở đây, nhưng tạm thời chạy trực tiếp.
            clauses = encoder.generate_clauses()
            
            for s_name in sat_solver_names:
                method_fullname = f"{enc_name} + {s_name.capitalize()}"
                print(f"Chạy {method_fullname}...")
                
                solver = SATRunner(n, s_name, clauses)
                res = execute_with_limits(solver, method_fullname)
                
                print(f"--> Kết quả: {res['status']} | Thời gian: {res['time']:.4f}s | RAM: {res['peak_ram_mb']:.2f}MB")
                if res["status"] == "Optimal" and n <= 12 and "solution" in res:
                    print_board(n, res["solution"], "SAT")
                
                logger.log_run(n, "SAT", method_fullname, res["status"], res["time"], res["peak_ram_mb"])
                comparator.add_result(n, "SAT", method_fullname, res["status"], res["time"], res["peak_ram_mb"])

        # 2. TRƯỜNG PHÁI CONSTRAINT PROGRAMMING (CP)
        cp_solvers = {
            "CP-SAT (Google)": CPSatRunner(n),
            "Cplex CP": CplexCPRunner(n)
        }
        for cp_name, solver in cp_solvers.items():
            print(f"\nChạy {cp_name} (N={n})...")
            res = execute_with_limits(solver, cp_name)
            print(f"--> Kết quả: {res['status']} | Thời gian: {res['time']:.4f}s | RAM: {res['peak_ram_mb']:.2f}MB")
            if res["status"] == "Optimal" and n <= 12 and "solution" in res:
                print_board(n, res["solution"], "CP")
            
            logger.log_run(n, "CP", cp_name, res["status"], res["time"], res["peak_ram_mb"])
            comparator.add_result(n, "CP", cp_name, res["status"], res["time"], res["peak_ram_mb"])

        # 3. TRƯỜNG PHÁI INTEGER LINEAR PROGRAMMING (ILP)
        ilp_solvers = {
            "Gurobi ILP": GurobiRunner(n),
            "Cplex MIP": CplexMIPRunner(n)
        }
        for ilp_name, solver in ilp_solvers.items():
            print(f"\nChạy {ilp_name} (N={n})...")
            res = execute_with_limits(solver, ilp_name)
            print(f"--> Kết quả: {res['status']} | Thời gian: {res['time']:.4f}s | RAM: {res['peak_ram_mb']:.2f}MB")

            if res["status"] == "Optimal" and n <= 12 and "solution" in res:
                print_board(n, res["solution"], "CP")

            logger.log_run(n, "ILP", ilp_name, res["status"], res["time"], res["peak_ram_mb"])
            comparator.add_result(n, "ILP", ilp_name, res["status"], res["time"], res["peak_ram_mb"])

    # Kết thúc vòng lặp, kiểm tra chéo và xuất báo cáo
    print("\nKiểm tra chéo kết quả (Cross-Validation):", "HỢP LỆ" if comparator.cross_validate_correctness() else "CÓ LỖI")
    
    print("\nBẢNG TỔNG HỢP HIỆU NĂNG:")
    print(comparator.generate_summary_report())
    
    # Lưu ra CSV để bạn chèn vào báo cáo
    comparator.get_raw_dataframe().to_csv("nqueens_benchmark_results.csv", index=False)
    logger.finish()
    print("\n[HOÀN THÀNH] Toàn bộ dữ liệu đã được đẩy lên Weights & Biases và lưu tại nqueens_benchmark_results.csv")