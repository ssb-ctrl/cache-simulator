#!/usr/bin/env python3

"""Generate memory-access traces. Each line:  R 0xADDR  or  W 0xADDR

Patterns
  seq       sequential 4-byte reads, repeated        (spatial + temporal locality)
  stride    reads every <stride> elements            (poor spatial locality)
  random    uniform random reads in a range          (no locality)
  conflict  K blocks that all map to the same set    (shows associativity)
  matmul_ijk / matmul_ikj   C = A*B with two loop orders (same maths, different locality)
"""

import argparse, random


def seq(n=4096, passes=4):
    for _ in range(passes):
        for i in range(n):
            yield "R", 4 * i


def stride(n=4096, stride=16, passes=2):
    for _ in range(passes):
        for i in range(n):
            yield "R", 4 * stride * i


def rand_pat(count=200000, span=48 * 1024, seed=1):
    r = random.Random(seed)
    for _ in range(count):
        yield "R", 4 * r.randrange(span // 4)


def conflict(k=3, spacing=4096, reps=5000):
    for _ in range(reps):
        for j in range(k):
            yield "R", j * spacing


def matmul(order="ijk", n=32):
    A, B, C = 0, 4 * n * n, 8 * n * n
    a = lambda i, j: A + 4 * (i * n + j)
    b = lambda i, j: B + 4 * (i * n + j)
    c = lambda i, j: C + 4 * (i * n + j)
    if order == "ijk":
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    yield "R", a(i, k)
                    yield "R", b(k, j)  # walks DOWN a column of B: stride = n*4 bytes
                yield "W", c(i, j)
    else:  # ikj
        for i in range(n):
            for k in range(n):
                yield "R", a(i, k)
                for j in range(n):
                    yield "R", b(k, j)  # walks ALONG a row of B: stride = 4 bytes
                    yield "R", c(i, j)
                    yield "W", c(i, j)


def cyclic(ws=5120):
    for _ in range(200):
        for off in range(0, ws, 4):
            yield "R", off


def write_trace(path, it):
    with open(path, "w") as f:
        for op, addr in it:
            f.write(f"{op} 0x{addr:x}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "pattern",
        choices=[
            "seq",
            "stride",
            "random",
            "conflict",
            "matmul_ijk",
            "matmul_ikj",
            "cyclic",
        ],
    )
    p.add_argument("out")
    p.add_argument("--n", type=int, default=32, help="matrix size for matmul")
    a = p.parse_args()
    gens = {
        "seq": seq,
        "stride": stride,
        "random": rand_pat,
        "conflict": conflict,
        "cyclic": cyclic,
        "matmul_ijk": lambda: matmul("ijk", a.n),
        "matmul_ikj": lambda: matmul("ikj", a.n),
    }
    write_trace(a.out, gens[a.pattern]())
    print("wrote", a.out)
