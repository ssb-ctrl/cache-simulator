#!/usr/bin/env python3
"""Runs 5 experiments with the C++ cache simulator and prints/saves the results.
Usage:  make && python3 experiments.py
Outputs: results/*.csv (+ results/*.png if matplotlib is installed)"""

import os, subprocess, csv
import gen_trace as g

SIM = "./cache_sim"
os.makedirs("traces", exist_ok=True)
os.makedirs("results", exist_ok=True)


def trace(name, it):
    p = f"traces/{name}.txt"
    if not os.path.exists(p):
        g.write_trace(p, it)
    return p


def run(tr, l1=(4096, 64, 2), l2=None, policy="lru"):
    cmd = [
        SIM,
        tr,
        "--l1-size",
        str(l1[0]),
        "--l1-block",
        str(l1[1]),
        "--l1-assoc",
        str(l1[2]),
        "--policy",
        policy,
        "--csv",
    ]
    if l2:
        cmd += [
            "--l2-size",
            str(l2[0]),
            "--l2-block",
            str(l2[1]),
            "--l2-assoc",
            str(l2[2]),
        ]
    v = (
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        .stdout.strip()
        .split(",")
    )
    return dict(
        accesses=int(v[0]),
        misses=int(v[1]),
        miss_rate=float(v[2]) * 100,
        writebacks=int(v[3]),
        l2_miss_rate=float(v[4]) * 100,
        amat=float(v[5]),
    )


def save(name, header, rows):
    with open(f"results/{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print("  ".join(f"{h:>14}" for h in header))
    for r in rows:
        print(
            "  ".join(f"{(f'{x:.2f}' if isinstance(x, float) else x):>14}" for x in r)
        )
    print()


def plot(name, title, xlabel, ylabel, series, logx=False):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    plt.figure(figsize=(6, 4))
    for label, xs, ys in series:
        plt.plot(xs, ys, marker="o", label=label)
    if logx:
        plt.xscale("log", base=2)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"results/{name}.png", dpi=120)
    plt.close()


# ---------------------------------------------------------------- E1
print("E1: cache size vs. matrix-multiply loop order (64B blocks, 2-way)")
ijk = trace("matmul_ijk", g.matmul("ijk"))
ikj = trace("matmul_ikj", g.matmul("ikj"))
sizes = [1024, 2048, 4096, 8192, 16384, 32768]
rows, s1, s2 = [], [], []
for s in sizes:
    a, b = run(ijk, (s, 64, 2)), run(ikj, (s, 64, 2))
    rows.append([s, a["miss_rate"], a["misses"], b["miss_rate"], b["misses"]])
    s1.append(a["miss_rate"])
    s2.append(b["miss_rate"])
save(
    "e1_cache_size",
    ["size_bytes", "ijk_miss%", "ijk_misses", "ikj_miss%", "ikj_misses"],
    rows,
)
plot(
    "e1_cache_size",
    "Matrix multiply: loop order vs cache size",
    "L1 size (bytes)",
    "miss rate (%)",
    [("ijk", sizes, s1), ("ikj", sizes, s2)],
    logx=True,
)

# ---------------------------------------------------------------- E2
print("E2: block size (4KB, 2-way) - spatial locality")
sq = trace("seq", g.seq())
rn = trace("random", g.rand_pat())
blocks = [8, 16, 32, 64, 128, 256]
rows, s1, s2 = [], [], []
for b in blocks:
    a, c = run(sq, (4096, b, 2)), run(rn, (4096, b, 2))
    rows.append([b, a["miss_rate"], c["miss_rate"]])
    s1.append(a["miss_rate"])
    s2.append(c["miss_rate"])
save("e2_block_size", ["block_bytes", "sequential_miss%", "random_miss%"], rows)
plot(
    "e2_block_size",
    "Block size vs miss rate",
    "block size (bytes)",
    "miss rate (%)",
    [("sequential", blocks, s1), ("random", blocks, s2)],
    logx=True,
)

# ---------------------------------------------------------------- E3
print("E3: associativity (4KB cache, 3 blocks that all map to the same set)")
cf = trace("conflict", g.conflict())
rows = []
for w in [1, 2, 4, 8]:
    a = run(cf, (4096, 64, w))
    rows.append([w, a["miss_rate"]])
save("e3_associativity", ["ways", "miss%"], rows)
plot(
    "e3_associativity",
    "Associativity on a conflict-heavy trace",
    "ways",
    "miss rate (%)",
    [("conflict", [r[0] for r in rows], [r[1] for r in rows])],
)

# ---------------------------------------------------------------- E4
print("E4: adding an L2 (random accesses over 48KB; L1=4KB, L2=64KB 8-way)")
rows = []
a = run(rn, (4096, 64, 2))
rows.append(["L1 only", a["miss_rate"], 0.0, a["amat"]])
a = run(rn, (4096, 64, 2), (65536, 64, 8))
rows.append(["L1 + L2", a["miss_rate"], a["l2_miss_rate"], a["amat"]])
save("e4_l2", ["config", "L1_miss%", "L2_local_miss%", "AMAT_cycles"], rows)

# ---------------------------------------------------------------- E5
print("E5: replacement policy (loop over 5KB working set, 4KB 4-way cache)")
cy = trace("cyclic", g.cyclic())
rows = []
for p in ["lru", "fifo", "random"]:
    a = run(cy, (4096, 64, 4), policy=p)
    rows.append([p, a["miss_rate"]])
save("e5_policy", ["policy", "miss%"], rows)
