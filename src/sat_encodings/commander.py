import itertools
from .base_encoder import BaseEncoder

class CommanderEncoder(BaseEncoder):
    def encode_amo(self, variables: list[int]):
        self._commander_recursive(variables)

    def _commander_recursive(self, variables: list[int]):
        n_vars = len(variables)
        if n_vars <= 1:
            return
        
        # Nếu số biến nhỏ, dùng phương pháp Binomial (Pairwise) thông thường
        if n_vars <= 3:
            for v1, v2 in itertools.combinations(variables, 2):
                self.add_clause([-v1, -v2])
            return

        # Chia các biến thành các nhóm, mỗi nhóm tối đa 3 biến
        group_size = 3
        groups = [variables[i:i + group_size] for i in range(0, n_vars, group_size)]
        commanders = []

        for group in groups:
            # 1. AMO cho từng nhóm nội bộ (Pairwise)
            for v1, v2 in itertools.combinations(group, 2):
                self.add_clause([-v1, -v2])
            
            # Cấp phát 1 biến chỉ huy cho nhóm
            cmd_var = self.new_aux_var()
            commanders.append(cmd_var)
            
            # 2. Nếu bất kỳ biến nào trong nhóm là True, biến chỉ huy phải là True
            for var in group:
                self.add_clause([-var, cmd_var])
                
            # 3. Nếu biến chỉ huy là True, phải có ít nhất 1 biến trong nhóm là True
            # (cmd_var => var_1 OR var_2 OR var_3) <=> (-cmd_var OR var_1 OR var_2 OR var_3)
            self.add_clause([-cmd_var] + group)

        # Đệ quy áp dụng AMO cho danh sách các biến chỉ huy
        self._commander_recursive(commanders)