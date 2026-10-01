from .base_encoder import BaseEncoder

class SequentialCounterEncoder(BaseEncoder):
    def encode_amo(self, variables: list[int]):
        n = len(variables)
        if n <= 1:
            return

        # Cấp phát n-1 biến phụ đóng vai trò như các thanh ghi trạng thái (s_1 ... s_{n-1})
        s = [self.new_aux_var() for _ in range(n - 1)]

        # Ràng buộc cơ sở cho phần tử đầu tiên
        self.add_clause([-variables[0], s[0]])

        # Ràng buộc cho các phần tử ở giữa
        for i in range(1, n - 1):
            # 1. Nếu biến hiện tại x_i là True, trạng thái s_i cũng phải là True
            self.add_clause([-variables[i], s[i]])
            
            # 2. Nếu trạng thái trước đó s_{i-1} là True, trạng thái hiện tại s_i cũng nối tiếp là True
            self.add_clause([-s[i-1], s[i]])
            
            # 3. Ràng buộc AMO cốt lõi: Không thể có x_i = True VÀ trạng thái trước đó s_{i-1} = True
            # (Nếu xảy ra, tức là có > 1 biến là True) -> (-x_i OR -s_{i-1})
            self.add_clause([-variables[i], -s[i-1]])

        # Ràng buộc cho phần tử cuối cùng: Không thể x_n = True VÀ s_{n-1} = True
        self.add_clause([-variables[n-1], -s[n-2]])