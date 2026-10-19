// cache_sim.cpp - configurable 1- or 2-level cache simulator (trace driven)
// Write-back + write-allocate. Replacement: LRU / FIFO / random.
#include <bits/stdc++.h>
#include <ostream>
using namespace std;
typedef unsigned long long u64;

enum Policy { LRU, FIFO, RANDOM };

struct Line {
  bool valid = false, dirty = false;
  u64 tag = 0, stamp = 0;
};

class Cache {
public:
  string name;
  int sizeB, blockB, assoc, numSets;
  Policy policy;
  Cache *next = nullptr; // next level (nullptr = main memory)
  vector<vector<Line>> sets;
  u64 clk = 0;
  long long accesses = 0, hits = 0, misses = 0, compulsory = 0, writebacks = 0;
  unordered_set<u64> seen; // blocks ever touched (to count compulsory misses)

  Cache(string n, int size, int block, int ways, Policy p)
      : name(n), sizeB(size), blockB(block), assoc(ways), policy(p) {
    if (size <= 0 || block <= 0 || ways <= 0 || size % (block * ways) != 0)
      throw runtime_error(name + ": size must be a multiple of block*assoc");
    numSets = size / (block * ways);
    sets.assign(numSets, vector<Line>(ways));
  }

  void access(u64 addr, bool isWrite) {
    accesses++;
    clk++;
    u64 blk = addr / blockB; // block number
    int set = blk % numSets; // index bits
    u64 tag = blk / numSets; // tag bits
    auto &ways = sets[set];

    for (auto &l : ways) // 1) look for a hit
      if (l.valid && l.tag == tag) {
        hits++;
        if (policy == LRU)
          l.stamp = clk; // LRU: refresh on every use
        if (isWrite)
          l.dirty = true;
        return;
      }

    misses++; // 2) miss
    if (seen.insert(blk).second)
      compulsory++;

    int v = -1; // pick a victim: empty way first
    for (int w = 0; w < assoc; w++)
      if (!ways[w].valid) {
        v = w;
        break;
      }
    if (v < 0) {
      if (policy == RANDOM)
        v = rand() % assoc;
      else {
        v = 0;
        for (int w = 1; w < assoc; w++)
          if (ways[w].stamp < ways[v].stamp)
            v = w;
      }
    }
    Line &vic = ways[v];
    if (vic.valid && vic.dirty) { // write-back of dirty victim
      writebacks++;
      if (next)
        next->access((vic.tag * numSets + set) * (u64)blockB, true);
    }
    if (next)
      next->access(addr, false); // fetch the block from the next level
    vic.valid = true;
    vic.dirty = isWrite;
    vic.tag = tag;
    vic.stamp = clk; // FIFO keeps this stamp
  }
  double missRate() const { return accesses ? (double)misses / accesses : 0.0; }
};

int main(int argc, char **argv) {
  if (argc < 2) {
    cerr << "usage: cache_sim trace.txt [--l1-size B --l1-block B --l1-assoc "
            "N]\n"
            "                 [--l2-size B --l2-block B --l2-assoc N]\n"
            "                 [--policy lru|fifo|random] [--l1-hit C --l2-hit "
            "C --mem C] [--csv]\n";
    return 1;
  }
  map<string, string> opt = {{"--l1-size", "4096"}, {"--l1-block", "64"},
                             {"--l1-assoc", "2"},   {"--l2-size", "0"},
                             {"--l2-block", "64"},  {"--l2-assoc", "8"},
                             {"--policy", "lru"},   {"--l1-hit", "1"},
                             {"--l2-hit", "10"},    {"--mem", "100"}};
  bool csv = false;
  for (int i = 2; i < argc; i++) {
    string a = argv[i];
    if (a == "--csv")
      csv = true;
    else if (opt.count(a) && i + 1 < argc)
      opt[a] = argv[++i];
    else {
      cerr << "unknown/incomplete option: " << a << "\n";
      return 1;
    }
  }
  try {
    Policy pol = opt["--policy"] == "fifo"     ? FIFO
                 : opt["--policy"] == "random" ? RANDOM
                                               : LRU;
    Cache l1("L1", stoi(opt["--l1-size"]), stoi(opt["--l1-block"]),
             stoi(opt["--l1-assoc"]), pol);
    bool hasL2 = stoi(opt["--l2-size"]) > 0;
    Cache l2("L2", hasL2 ? stoi(opt["--l2-size"]) : 64, stoi(opt["--l2-block"]),
             hasL2 ? stoi(opt["--l2-assoc"]) : 1, pol);
    if (hasL2)
      l1.next = &l2;

    ifstream f(argv[1]);
    if (!f) {
      cerr << "cannot open trace " << argv[1] << "\n";
      return 1;
    }
    string op, addrs;
    while (f >> op >> addrs)
      l1.access(strtoull(addrs.c_str(), nullptr, 0), op == "W" || op == "w");

    double h1 = stod(opt["--l1-hit"]), h2 = stod(opt["--l2-hit"]),
           mem = stod(opt["--mem"]);
    // AMAT = hit_time(L1) + miss_rate(L1) * miss_penalty(L1)
    double amat = hasL2 ? h1 + l1.missRate() * (h2 + l2.missRate() * mem)
                        : h1 + l1.missRate() * mem;
    if (csv) {
      printf("%lld,%lld,%.6f,%lld,%.6f,%.4f\n", l1.accesses, l1.misses,
             l1.missRate(), l1.writebacks, hasL2 ? l2.missRate() : 0.0, amat);
      return 0;
    }
    for (Cache *c : {&l1, &l2}) {
      if (c == &l2 && !hasL2)
        break;
      printf("=== %s: %d B, %d B blocks, %d-way, %d sets ===\n",
             c->name.c_str(), c->sizeB, c->blockB, c->assoc, c->numSets);
      printf("  accesses   : %lld\n  hits       : %lld\n  misses     : %lld "
             "(compulsory: %lld)\n  miss rate  : %.2f%%\n  writebacks : %lld\n",
             c->accesses, c->hits, c->misses, c->compulsory,
             100 * c->missRate(), c->writebacks);
    }
    printf("AMAT = %.2f cycles  (L1 hit=%g%s, memory=%g)\n", amat, h1,
           hasL2 ? (", L2 hit=" + to_string((int)h2)).c_str() : "", mem);
  } catch (exception &e) {
    cerr << "error: " << e.what() << "\n";
    return 1;
  }
}
