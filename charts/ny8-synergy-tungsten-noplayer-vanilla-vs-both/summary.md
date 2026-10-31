| Metric | Vanilla 1.22.7, no mods | Synergy + Tungsten together (vs baseline) |
|---|---|---|
| startup_fresh_s | 15.86 s | 16.21 s (+2.3% worse) |
| startup_existing_s | 10.31 s | 10.78 s (+4.5% worse) |
| worldgen_wall_s | 39.00 s | 38.96 s (-0.1%) |
| reload_wall_s | 1.70 s | 1.58 s (-7.2% better) |
| worldgen_columns_per_s | 43.11 columns/s | 43.15 columns/s (+0.1%) |
| worldgen_cpu_s | 43.13 s | 42.81 s (-0.7%) |
| idle_tick_mean_ms | 1.16 ms | 0.90 ms (-22.1% better) |
| idle_tick_median_ms | 1.09 ms | 0.84 ms (-22.9% better) |
| idle_tick_p95_ms | 1.81 ms | 1.46 ms (-19.1% better) |
| idle_tick_p99_ms | 2.31 ms | 1.94 ms (-15.9% better) |
| idle_tick_max_ms | 3.56 ms | 2.94 ms (-17.6% better) |
| entities_tick_mean_ms | 3.88 ms | 3.58 ms (-7.6% better) |
| entities_tick_median_ms | 3.35 ms | 2.95 ms (-12.1% better) |
| entities_tick_p95_ms | 6.03 ms | 5.92 ms (-1.8%) |
| entities_tick_p99_ms | 11.98 ms | 15.23 ms (+27.1% worse) |
| entities_tick_max_ms | 151.01 ms | 155.33 ms (+2.9% worse) |
| peak_working_set_mb | 1,762.84 MB | 1,788.28 MB (+1.4%) |
| heap_after_worldgen_mb | 1,215.55 MB | 1,221.02 MB (+0.4%) |
| heap_after_entities_mb | 1,167.95 MB | 1,165.38 MB (-0.2%) |
| peak_working_set_reload_mb | 1,441.00 MB | 1,428.95 MB (-0.8%) |
| worldgen_cpu_ms | 43,126.59 ms | 42,809.77 ms (-0.7%) |
| worldgen_gc_pause_ms | 963.83 ms | 899.76 ms (-6.6% better) |
| worldgen_gc_gen0 | 351.00 gen0 | 266.50 gen0 (-24.1% better) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 907.60 ms | 761.71 ms (-16.1% better) |
| idle_gc_pause_ms | 12.37 ms | 11.02 ms (-10.9% better) |
| idle_gc_gen0 | 11.00 gen0 | 11.00 gen0 (+0.0%) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) |
| entities_cpu_ms | 7,124.11 ms | 6,611.83 ms (-7.2% better) |
| entities_gc_pause_ms | 209.93 ms | 203.40 ms (-3.1% better) |
| entities_gc_gen0 | 57.50 gen0 | 52.50 gen0 (-8.7% better) |
| entities_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) |
| idle_cpu_pct_of_one_core | 4.51 % | 3.78 % (-16.2% better) |
| entities_cpu_pct_of_one_core | 15.85 % | 14.72 % (-7.1% better) |
| idle_tps | 29.81 ticks/s | 29.78 ticks/s (-0.1%) |
| entities_tps | 29.80 ticks/s | 29.79 ticks/s (-0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |