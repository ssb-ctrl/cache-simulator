# Project 1 – Cache Simulator & Memory Performance Analysis

## Idea
A CPU is much faster than main memory, so caches keep recently used data close. This simulator reads a **trace** of memory accesses (`R 0x1a40`, `W 0x2000`, ...) and tells you how many hit/miss in a configurable L1 (and optional L2) cache. Then you run experiments and explain the results — that is the "performance analysis" the JD asks for.

## Files
- `cache_sim.cpp` – the simulator (write-back, write-allocate, LRU/FIFO/random)
- `gen_trace.py` – makes traces: sequential, strided, random, conflict, matrix-multiply (2 loop orders)
- `experiments.py` – runs 5 experiments, prints tables, saves CSV (+ PNG plots if matplotlib is installed)

## Run
```
make
python3 experiments.py                       # all experiments
python3 gen_trace.py seq t.txt && ./cache_sim t.txt --l1-size 4096 --l1-block 64 --l1-assoc 2
./cache_sim t.txt --l2-size 65536 --l2-assoc 8   # add an L2
```

## How the core works (the only 3 ideas)
1. Address → `block = addr / blockSize`, `set = block % numSets`, `tag = block / numSets`.
2. Look in that set's ways. Tag match = **hit**. Otherwise **miss**: evict the least-recently-used way (if dirty, write it back), fetch the new block.
3. `AMAT = L1 hit + L1 miss rate × (L2 hit + L2 miss rate × memory)`.

## Results you should see (and why)
| Experiment | Result | Reason |
|---|---|---|
| E1 loop order | `ikj` has far fewer misses than `ijk` at small cache sizes (e.g. 2.4% vs 52% at 2 KB) | `ijk` walks down a column of B (big stride, no spatial locality); `ikj` walks along rows |
| E2 block size | Sequential miss rate halves each time block size doubles; random stays ~91% | Bigger blocks exploit **spatial locality**; random access has none |
| E3 associativity | 1-way and 2-way: 100% misses; 4-way: ~0% | 3 blocks fight for one set; 4 ways can hold them. (2-way + LRU on a 3-block cycle is the classic worst case) |
| E4 L2 | AMAT drops from ~93 to ~11 cycles | L1 misses are caught by the L2 instead of paying 100 cycles to memory |
| E5 policy | Random beats LRU/FIFO on a loop slightly bigger than the cache | LRU evicts exactly the block needed next |

## Interview questions to prepare
- Tag/index/offset: how many bits for a 4 KB, 2-way, 64 B-block cache? (32 sets → 5 index, 6 offset)
- Compulsory vs capacity vs conflict misses — which experiment shows each?
- Why does GPU code care about memory coalescing? (same spatial-locality idea)
- What would change for write-through / no-write-allocate?

## Extension ideas (optional)
Add a prefetcher (fetch next block on miss) and re-run E1; add a 3rd cache level; add a victim cache.
