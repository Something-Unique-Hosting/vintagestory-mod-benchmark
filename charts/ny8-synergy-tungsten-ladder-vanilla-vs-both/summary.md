| Metric | Vanilla 1.22.7, no mods | Synergy + Tungsten together (vs baseline) |
|---|---|---|
| startup_fresh_s | 15.63 s | 16.89 s (+8.1% worse) |
| worldgen_wall_s | 39.48 s | 38.95 s (-1.3%) |
| worldgen_columns_per_s | 42.58 columns/s | 43.16 columns/s (+1.3%) |
| worldgen_cpu_s | 43.63 s | 43.08 s (-1.3%) |
| idle_tick_mean_ms | 1.45 ms | 1.05 ms (-27.3% better) |
| idle_tick_median_ms | 1.41 ms | 1.07 ms (-24.4% better) |
| idle_tick_p95_ms | 2.03 ms | 1.58 ms (-22.3% better) |
| idle_tick_p99_ms | 2.51 ms | 2.50 ms (-0.4%) |
| idle_tick_max_ms | 3.13 ms | 3.06 ms (-2.3% better) |
| peak_working_set_mb | 2,504.47 MB | 2,573.77 MB (+2.8% worse) |
| heap_after_worldgen_mb | 1,216.50 MB | 1,217.16 MB (+0.1%) |
| worldgen_cpu_ms | 43,634.51 ms | 43,082.08 ms (-1.3%) |
| worldgen_gc_pause_ms | 995.82 ms | 933.16 ms (-6.3% better) |
| worldgen_gc_gen0 | 351.00 gen0 | 268.00 gen0 (-23.6% better) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 1,088.24 ms | 856.66 ms (-21.3% better) |
| idle_gc_pause_ms | 11.94 ms | 13.73 ms (+15.0% worse) |
| idle_gc_gen0 | 11.00 gen0 | 11.00 gen0 (+0.0%) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) |
| idle_cpu_pct_of_one_core | 5.41 % | 4.27 % (-21.2% better) |
| idle_tps | 29.84 ticks/s | 29.83 ticks/s (-0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |