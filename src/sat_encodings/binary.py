import math
from .base_encoder import BaseEncoder

class BinaryEncoder(BaseEncoder):
    """
    Cài đặt thuật toán mã hóa Binary cho ràng buộc AMO.
    Thuật toán này giảm số lượng mệnh đề từ O(N^2) của Binomial xuống còn O(N log N)
    bằng cách sử dụng thêm O(log N) biến phụ (auxiliary variables).
    """
    def encode_amo(self, variables: list[int]):
        n_vars = len(variables)
        
        # Nếu có 1 hoặc 0 biến, ràng buộc AMO mặc định thỏa mãn, không cần sinh clauses
        if n_vars <= 1:
            return

        # Tính số lượng bit cần thiết (biến phụ) để biểu diễn ID của n_vars
        num_bits = math.ceil(math.log2(n_vars))
        
        # Cấp phát các biến phụ (B_0, B_1, ..., B_{m-1}) thông qua hàm từ class cha
        aux_vars = [self.new_aux_var() for _ in range(num_bits)]

        # Duyệt qua từng biến x_i trong tập variables
        for i, var in enumerate(variables):
            # Với mỗi biến x_i, nếu x_i = True, nó sẽ ép các biến phụ B_j 
            # nhận giá trị đúng với chuỗi nhị phân của số nguyên i.
            for j in range(num_bits):
                # Kiểm tra bit thứ j của số nguyên i có phải là 1 hay không
                bit_is_one = (i & (1 << j)) != 0
                
                if bit_is_one:
                    # Ràng buộc: x_i kéo theo B_j (Nếu x_i=1 thì B_j=1)
                    # Biểu diễn CNF: ¬x_i ∨ B_j
                    self.add_clause([-var, aux_vars[j]])
                else:
                    # Ràng buộc: x_i kéo theo ¬B_j (Nếu x_i=1 thì B_j=0)
                    # Biểu diễn CNF: ¬x_i ∨ ¬B_j
                    self.add_clause([-var, -aux_vars[j]])