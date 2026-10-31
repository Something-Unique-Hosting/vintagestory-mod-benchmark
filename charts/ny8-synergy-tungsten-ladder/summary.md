| Metric | Vanilla 1.22.7, no mods | Synergy 1.1.25 (vs baseline) | Tungsten 1.3.7 (vs baseline) | All 2 mods together (vs baseline) |
|---|---|---|---|---|
| startup_fresh_s | 15.63 s | 16.37 s (+4.8% worse) | 17.00 s (+8.8% worse) | 16.89 s (+8.1% worse) |
| worldgen_wall_s | 39.48 s | 39.24 s (-0.6%) | 39.02 s (-1.1%) | 38.95 s (-1.3%) |
| worldgen_columns_per_s | 42.58 columns/s | 42.84 columns/s (+0.6%) | 43.08 columns/s (+1.2%) | 43.16 columns/s (+1.3%) |
| worldgen_cpu_s | 43.63 s | 43.26 s (-0.9%) | 43.29 s (-0.8%) | 43.08 s (-1.3%) |
| idle_tick_mean_ms | 1.45 ms | 0.87 ms (-40.0% better) | 1.52 ms (+4.9% worse) | 1.05 ms (-27.3% better) |
| idle_tick_median_ms | 1.41 ms | 0.86 ms (-39.5% better) | 1.48 ms (+4.6% worse) | 1.07 ms (-24.4% better) |
| idle_tick_p95_ms | 2.03 ms | 1.42 ms (-30.3% better) | 2.07 ms (+1.6%) | 1.58 ms (-22.3% better) |
| idle_tick_p99_ms | 2.51 ms | 1.95 ms (-22.4% better) | 2.73 ms (+8.7% worse) | 2.50 ms (-0.4%) |
| idle_tick_max_ms | 3.13 ms | 3.46 ms (+10.4% worse) | 3.64 ms (+16.2% worse) | 3.06 ms (-2.3% better) |
| peak_working_set_mb | 2,504.47 MB | 2,543.45 MB (+1.6%) | 2,593.44 MB (+3.6% worse) | 2,573.77 MB (+2.8% worse) |
| heap_after_worldgen_mb | 1,216.50 MB | 1,222.13 MB (+0.5%) | 1,219.61 MB (+0.3%) | 1,217.16 MB (+0.1%) |
| worldgen_cpu_ms | 43,634.51 ms | 43,259.04 ms (-0.9%) | 43,293.57 ms (-0.8%) | 43,082.08 ms (-1.3%) |
| worldgen_gc_pause_ms | 995.82 ms | 1,011.95 ms (+1.6%) | 973.47 ms (-2.2% better) | 933.16 ms (-6.3% better) |
| worldgen_gc_gen0 | 351.00 gen0 | 352.00 gen0 (+0.3%) | 267.00 gen0 (-23.9% better) | 268.00 gen0 (-23.6% better) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 1,088.24 ms | 735.73 ms (-32.4% better) | 1,132.11 ms (+4.0% worse) | 856.66 ms (-21.3% better) |
| idle_gc_pause_ms | 11.94 ms | 13.17 ms (+10.3% worse) | 13.29 ms (+11.3% worse) | 13.73 ms (+15.0% worse) |
| idle_gc_gen0 | 11.00 gen0 | 12.00 gen0 (+9.1% worse) | 11.00 gen0 (+0.0%) | 11.00 gen0 (+0.0%) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) | 0.00 gen2 (+nan% worse) | 0.00 gen2 (+nan% worse) |
| idle_cpu_pct_of_one_core | 5.41 % | 3.64 % (-32.7% better) | 5.63 % (+4.0% worse) | 4.27 % (-21.2% better) |
| idle_tps | 29.84 ticks/s | 29.82 ticks/s (-0.1%) | 29.82 ticks/s (-0.1%) | 29.83 ticks/s (-0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |