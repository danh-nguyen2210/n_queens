# N-Queens: đối chiếu SAT, CP và ILP

Mã thực nghiệm so sánh 5 mã hóa SAT trên Glucose3 và CaDiCaL195 với CP-SAT, CP Optimizer, Gurobi và CPLEX MIP.

## Thiết lập (PowerShell, Python 3.13)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

CP Optimizer yêu cầu cài đặt IBM CPLEX Optimization Studio; Gurobi/CPLEX có thể cần giấy phép đủ quy mô. Các gói phải được cài trong cùng môi trường Python.

## Chạy thử ngắn

Từ thư mục gốc của repo:

```powershell
python main_experiment.py --sizes 4 8 --encodings binomial commander --sat-solvers glucose3 --baselines cp-sat --repeats 1 --timeout 10 --ram-mb 2048
python analyze_results.py
```

Lệnh đầu lưu mỗi lần chạy vào `results/<timestamp>/`; lệnh thứ hai tổng hợp lần chạy mới nhất thành `summary.csv`. Biểu đồ trong `results/` thuộc về bộ thực nghiệm đầy đủ. Nên kiểm tra cột `Status` và `Valid` trong `runs.csv`.

## Bộ kết quả đi kèm

Các tệp `results/runs.csv`, `results/summary.csv`, `results/environment.json` và 5 biểu đồ ghi lại thí nghiệm trên Windows/Python 3.13.7, 18 kích thước, 14 cấu hình, 3 lần lặp, giới hạn 100 giây mỗi lượt. Đây là dữ liệu đã thu, khác với đầu ra chạy thử vừa tạo.

Để tổng hợp lại bản sao của bộ dữ liệu, đưa `runs.csv` và `environment.json` vào cùng một thư mục khác rồi chạy `python analyze_results.py <duong-dan-runs.csv> --plot`. Công cụ phân tích có thể chỉnh sửa dữ liệu đầu vào nếu có dòng `totalizer`.

Xem tham số đầy đủ: `python main_experiment.py --help`.
