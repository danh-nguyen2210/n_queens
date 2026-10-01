from abc import ABC, abstractmethod

class BaseEncoder(ABC):
    """
    Class cha (Abstract Base Class) định nghĩa bộ khung cho tất cả các phương pháp SAT Encoding.
    Mọi class con (Binomial, Binary, SequentialCounter,...) đều phải kế thừa class này
     và ghi đè (override) phương thức `encode_amo`.
    """
    def __init__(self, n: int):
        self.n = n
        self.clauses = []
        # Các biến chính cho bàn cờ N x N sẽ chiếm từ 1 đến N^2.
        # Biến phụ (auxiliary variables) cho các encoding phức tạp sẽ bắt đầu từ N^2 + 1.
        self.next_var_id = n * n + 1 

    def var(self, row: int, col: int) -> int:
        """
        Ánh xạ tọa độ (row, col) trên bàn cờ 2 chiều thành ID biến nguyên dương 1 chiều.
        PySAT yêu cầu các biến (variables) bắt đầu từ 1.
        """
        return row * self.n + col + 1

    def new_aux_var(self) -> int:
        """
        Cấp phát một ID biến phụ mới. Rất quan trọng cho Commander, Product, Sequential Counter.
        """
        var_id = self.next_var_id
        self.next_var_id += 1
        return var_id

    def add_clause(self, clause: list[int]):
        """Thêm một mệnh đề (clause) vào danh sách."""
        self.clauses.append(clause)

    def encode_alo(self, variables: list[int]):
        """
        Ràng buộc ALO (At-Least-One): Ít nhất một biến trong tập phải mang giá trị True.
        Với mọi thuật toán, ALO luôn chỉ là 1 mệnh đề (clause) chứa tất cả các biến.
        """
        if len(variables) > 0:
            self.add_clause(variables)

    @abstractmethod
    def encode_amo(self, variables: list[int]):
        """
        Ràng buộc AMO (At-Most-One): Không quá một biến trong tập mang giá trị True.
        ĐÂY LÀ HÀM CỐT LÕI MÀ CÁC THUẬT TOÁN (BINOMIAL, BINARY,...) SẼ CÀI ĐẶT KHÁC NHAU.
        """
        pass

    def encode_exactly_one(self, variables: list[int]):
        """
        Ràng buộc Exact-One (Chính xác một): Kết hợp ALO và AMO.
        Áp dụng cho các hàng (rows) và cột (cols) của bàn cờ N-Queens.
        """
        self.encode_alo(variables)
        self.encode_amo(variables)

    def generate_clauses(self) -> list[list[int]]:
        """
        Hàm chính (Template Method) quét qua toàn bộ bàn cờ để sinh ra tập clauses cuối cùng.
        """
        # 1. Ràng buộc Hàng (Rows): Mỗi hàng có đúng 1 quân hậu
        for i in range(self.n):
            row_vars = [self.var(i, j) for j in range(self.n)]
            self.encode_exactly_one(row_vars)

        # 2. Ràng buộc Cột (Cols): Mỗi cột có đúng 1 quân hậu
        for j in range(self.n):
            col_vars = [self.var(i, j) for i in range(self.n)]
            self.encode_exactly_one(col_vars)

        # 3. Ràng buộc Đường chéo chính (\): Có tối đa 1 quân hậu
        # Sử dụng thuộc tính (i - j) không đổi trên cùng một đường chéo chính
        for d in range(-self.n + 1, self.n):
            diag_vars = [self.var(i, i - d) for i in range(self.n) if 0 <= i - d < self.n]
            if len(diag_vars) > 1:
                self.encode_amo(diag_vars)

        # 4. Ràng buộc Đường chéo phụ (/): Có tối đa 1 quân hậu
        # Sử dụng thuộc tính (i + j) không đổi trên cùng một đường chéo phụ
        for d in range(2 * self.n - 1):
            anti_diag_vars = [self.var(i, d - i) for i in range(self.n) if 0 <= d - i < self.n]
            if len(anti_diag_vars) > 1:
                self.encode_amo(anti_diag_vars)

        return self.clauses