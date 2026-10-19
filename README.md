# Cache Simulator & Memory Performance Analysis

A trace-driven cache simulator written in C++, with Python scripts to generate memory traces and run experiments. It models a set-associative L1 cache with an optional L2, and reports hit/miss counts, miss rate and average memory access time (AMAT).

## Background

Main memory is much slower than the CPU, so a small fast memory (the cache) keeps recently used data close by. Caches work because programs show two kinds of locality:

- **Temporal locality**: data used recently is likely to be used again soon.
- **Spatial locality**: data near a recently used address is likely to be used soon.

The cache stores data in blocks (here 64 bytes). A memory address is split into three parts:

| Part | Meaning |
|---|---|
| Offset | byte position inside the block |
| Index | which set the block must go in |
| Tag | identifies which block currently sits in a way of that set |

In the code this is `block = addr / blockSize`, `set = block % numSets`, `tag = block / numSets`. Each set has N ways (the associativity). A lookup is a hit if any way in the set has a matching tag. On a miss, one way is chosen as the victim (LRU, FIFO or random) and replaced. The cache is write-back and write-allocate: a write only marks the block dirty, and the data goes to the next level when the block is evicted.

Performance is summarised by AMAT:

```
AMAT = L1 hit time + L1 miss rate x (L2 hit time + L2 miss rate x memory time)
```

All experiments use L1 hit = 1 cycle, L2 hit = 10 cycles, memory = 100 cycles.

## Files

| File | Purpose |
|---|---|
| `cache_sim.cpp` | the simulator |
| `gen_trace.py` | generates traces (sequential, strided, random, conflict, matrix multiply) |
| `experiments.py` | runs the experiments below, saves CSVs (and plots if matplotlib is installed) |
| `Makefile` | builds `cache_sim` |

## Build and run

```
make
python3 experiments.py
```

Run the simulator directly on a trace file (one access per line, `R 0x40` or `W 0x40`):

```
./cache_sim trace.txt --l1-size 4096 --l1-block 64 --l1-assoc 2
./cache_sim trace.txt --l2-size 65536 --l2-assoc 8 --policy lru
```

## Results

### 1. Matrix multiply loop order (64 B blocks, 2-way, 32x32 int matrices)

Both versions compute the same product. `ijk` walks down a column of B, so each access is 128 bytes from the last and lands in a different block. `ikj` walks along a row, so 16 consecutive ints share a block.

| L1 size | `ijk` miss rate | `ikj` miss rate |
|---|---|---|
| 1 KB | 52.40% | 2.68% |
| 2 KB | 52.40% | 2.44% |
| 4 KB | 6.48% | 0.56% |
| 8 KB | 4.06% | 0.35% |
| 16 KB | 0.29% | 0.19% |

Once the cache is large enough to hold the working set, the difference mostly disappears.

### 2. Block size (4 KB, 2-way)

| Block size | Sequential | Random |
|---|---|---|
| 8 B | 50.00% | 91.65% |
| 16 B | 25.00% | 91.50% |
| 32 B | 12.50% | 91.66% |
| 64 B | 6.25% | 91.68% |
| 128 B | 3.12% | 91.66% |
| 256 B | 1.56% | 91.71% |

Sequential access halves its miss rate each time the block doubles, since each fetch brings in more useful neighbours. Random access over 48 KB has no locality to exploit, so block size makes no difference.

### 3. Associativity (4 KB cache, 3 blocks that map to the same set)

| Ways | Miss rate |
|---|---|
| 1 | 100% |
| 2 | 100% |
| 4 | 0.02% |
| 8 | 0.02% |

With 1 or 2 ways the three blocks keep evicting each other (conflict misses). With LRU and a repeating cycle of 3 blocks, even 2 ways always evicts the block needed next. With 4 ways all three fit.

### 4. Adding an L2 (random accesses over 48 KB, L1 = 4 KB 2-way, L2 = 64 KB 8-way)

| Config | L1 miss rate | L2 miss rate | AMAT |
|---|---|---|---|
| L1 only | 91.68% | - | 92.68 cycles |
| L1 + L2 | 91.68% | 0.42% | 10.55 cycles |

The L1 misses just as often, but almost all of those misses are served by the L2 instead of memory.

### 5. Replacement policy (looping over a 5 KB array, 4 KB 4-way cache)

| Policy | Miss rate |
|---|---|
| LRU | 6.25% |
| FIFO | 6.25% |
| Random | 2.54% |

When a loop is slightly larger than the cache, LRU and FIFO always evict the block that is needed next. Random replacement gets lucky often enough to keep some blocks.

## Limitations

- Only addresses are simulated, not data values.
- Timing is a simple AMAT formula, not a cycle-accurate model.
- Write-backs to L2 are counted as L2 accesses, but there is no write buffer.
- The traces are synthetic, not taken from real programs.
