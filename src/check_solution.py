def check_solution(n, queens):
    # queens[i] là cột đặt hậu tại hàng i, tính từ 0.
    if not isinstance(queens, list) or len(queens) != n:
        return False
    for col in queens:
        if type(col) is not int or col < 0 or col >= n:
            return False
    if len(set(queens)) != n:
        return False
    if len(set(queens[i] + i for i in range(n))) != n:
        return False
    if len(set(queens[i] - i for i in range(n))) != n:
        return False
    return True


def check_result(n, result):
    if result["status"] == "Solved":
        result["valid"] = check_solution(n, result.get("solution"))
        if not result["valid"]:
            result["status"] = "Invalid"
            result["message"] = "Solver trả nghiệm không hợp lệ"
    elif result["status"] == "Unsat":
        result["valid"] = n in (2, 3)
        if not result["valid"]:
            result["status"] = "Invalid"
            result["message"] = "N-Queens có nghiệm khi N=1 hoặc N>=4"
    else:
        result["valid"] = ""
    return result


def print_board(queens):
    for col in queens:
        row = ["."] * len(queens)
        row[col] = "Q"
        print(" ".join(row))
