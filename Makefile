cache_sim: cache_sim.cpp
	g++ -O2 -std=c++17 -Wall -o cache_sim cache_sim.cpp
clean:
	rm -f cache_sim
