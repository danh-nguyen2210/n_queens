import itertools
import math


ENCODINGS = ["binomial", "binary", "commander", "product", "sequential"]


class NQueensEncoder:
    def __init__(self, n, encoding):
        if n < 1:
            raise ValueError("N phải là số nguyên dương")
        if encoding not in ENCODINGS:
            raise ValueError("Encoding không hợp lệ: " + encoding)
        self.n = n
        self.encoding = encoding
        self.clauses = []
        self.next_var = n * n + 1

    def var(self, row, col):
        return row * self.n + col + 1

    def new_var(self):
        v = self.next_var
        self.next_var += 1
        return v

    def pairwise(self, xs):
        for a, b in itertools.combinations(xs, 2):
            self.clauses.append([-a, -b])

    def binary(self, xs):
        bits = [self.new_var() for _ in range((len(xs) - 1).bit_length())]
        for i, x in enumerate(xs):
            for j, bit in enumerate(bits):
                # x đúng thì các bit phụ phải biểu diễn chỉ số i.
                if (i >> j) & 1:
                    self.clauses.append([-x, bit])
                else:
                    self.clauses.append([-x, -bit])

    def commander(self, xs):
        if len(xs) <= 3:
            self.pairwise(xs)
            return
        commanders = []
        for i in range(0, len(xs), 3):
            group = xs[i:i + 3]
            c = self.new_var()
            commanders.append(c)
            self.pairwise(group)
            for x in group:
                self.clauses.append([-x, c])
            self.clauses.append([-c] + group)
        self.commander(commanders)

    def product(self, xs):
        if len(xs) <= 4:
            self.pairwise(xs)
            return
        p = math.isqrt(len(xs))
        if p * p < len(xs):
            p += 1
        q = (len(xs) + p - 1) // p
        rows = [self.new_var() for _ in range(p)]
        cols = [self.new_var() for _ in range(q)]
        for i, x in enumerate(xs):
            self.clauses.append([-x, rows[i // q]])
            self.clauses.append([-x, cols[i % q]])
        self.product(rows)
        self.product(cols)

    def sequential(self, xs):
        s = [self.new_var() for _ in range(len(xs) - 1)]
        self.clauses.append([-xs[0], s[0]])
        for i in range(1, len(xs) - 1):
            self.clauses.append([-xs[i], s[i]])
            self.clauses.append([-s[i - 1], s[i]])
            self.clauses.append([-xs[i], -s[i - 1]])
        self.clauses.append([-xs[-1], -s[-1]])

    def amo(self, xs):
        if len(xs) <= 1:
            return
        if self.encoding == "binomial":
            self.pairwise(xs)
        elif self.encoding == "binary":
            self.binary(xs)
        elif self.encoding == "commander":
            self.commander(xs)
        elif self.encoding == "product":
            self.product(xs)
        elif self.encoding == "sequential":
            self.sequential(xs)

    def exactly_one(self, xs):
        self.clauses.append(xs)
        self.amo(xs)

    def build(self):
        # Reset để gọi build lần nữa không bị cộng dồn mệnh đề.
        self.clauses = []
        self.next_var = self.n * self.n + 1
        for i in range(self.n):
            self.exactly_one([self.var(i, j) for j in range(self.n)])
        for j in range(self.n):
            self.exactly_one([self.var(i, j) for i in range(self.n)])
        # Hai họ đường chéo có i-j hoặc i+j không đổi.
        for d in range(1 - self.n, self.n):
            self.amo([self.var(i, i - d) for i in range(self.n)
                      if 0 <= i - d < self.n])
        for d in range(2 * self.n - 1):
            self.amo([self.var(i, d - i) for i in range(self.n)
                      if 0 <= d - i < self.n])
        return self.clauses