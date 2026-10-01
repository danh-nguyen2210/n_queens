from .base_encoder import BaseEncoder
import itertools

class BinomialEncoder(BaseEncoder):
    """
    Cài đặt thuật toán mã hóa Binomial (còn gọi là Pairwise hoặc Naive).
    Đây là phương pháp cơ bản nhất để biểu diễn ràng buộc AMO (At-Most-One).
    """
    def encode_amo(self, variables: list[int]):
        """
        Mã hóa AMO bằng cách tạo ra các mệnh đề cho mọi cặp biến có thể có.
        Nếu có k biến, sẽ sinh ra k(k-1)/2 mệnh đề.
        Không sử dụng thêm biến phụ (auxiliary variables).
        """
        # Sử dụng itertools.combinations để lấy tất cả các cặp 2 biến khác nhau (var1, var2)
        for var1, var2 in itertools.combinations(variables, 2):
            # AMO: Không thể có cả 2 biến cùng là True.
            # Biểu diễn dưới dạng CNF: (NOT var1 OR NOT var2)
            # Trong PySAT, dấu trừ (-) thể hiện phép phủ định logic.
            self.add_clause([-var1, -var2])