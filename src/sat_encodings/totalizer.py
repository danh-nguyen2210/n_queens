from pysat.card import CardEnc, EncType
from .base_encoder import BaseEncoder

class TotalizerEncoder(BaseEncoder):
    """
    Sử dụng Totalizer Encoding thông qua thư viện PySAT.
    """
    def encode_amo(self, variables: list[int]):
        # Truyền top_id = self.next_var_id - 1 để PySAT cấp phát biến phụ 
        # ở vùng an toàn (lớn hơn N^2), tuyệt đối không dẫm đạp lên biến bàn cờ.
        cnf = CardEnc.atmost(
            lits=variables, 
            bound=1, 
            encoding=EncType.totalizer, 
            top_id=self.next_var_id - 1
        )
        
        self.clauses.extend(cnf.clauses)
        
        # Quét lại các clauses vừa sinh để đẩy mốc ID an toàn lên cao hơn,
        # chuẩn bị cho vòng lặp (hàng/cột/đường chéo) tiếp theo.
        if cnf.clauses:
            max_in_cnf = max(abs(lit) for clause in cnf.clauses for lit in clause)
            if max_in_cnf >= self.next_var_id:
                self.next_var_id = max_in_cnf + 1