import math
import itertools
from .base_encoder import BaseEncoder

class ProductEncoder(BaseEncoder):
    def encode_amo(self, variables: list[int]):
        n_vars = len(variables)
        if n_vars <= 1:
            return

        # Tính toán kích thước lưới p x q sao cho p * q >= n_vars
        p = math.ceil(math.sqrt(n_vars))
        
        # Cấp phát biến phụ cho các hàng và cột
        row_vars = [self.new_aux_var() for _ in range(p)]
        col_vars = [self.new_aux_var() for _ in range(p)]

        for i, var in enumerate(variables):
            r = i // p
            c = i % p
            
            # Nếu biến var là True, thì hàng r và cột c tương ứng phải là True
            self.add_clause([-var, row_vars[r]])
            self.add_clause([-var, col_vars[c]])

        # Áp dụng AMO (Pairwise) cho các biến hàng
        for r1, r2 in itertools.combinations(row_vars, 2):
            self.add_clause([-r1, -r2])

        # Áp dụng AMO (Pairwise) cho các biến cột
        for c1, c2 in itertools.combinations(col_vars, 2):
            self.add_clause([-c1, -c2])