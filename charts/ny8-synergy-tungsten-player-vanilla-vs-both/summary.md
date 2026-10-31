| Metric | Vanilla 1.22.7, no mods | Synergy + Tungsten together (vs baseline) |
|---|---|---|
| startup_fresh_s | 15.81 s | 15.71 s (-0.6%) |
| startup_existing_s | 10.74 s | 11.28 s (+5.0% worse) |
| worldgen_wall_s | 39.50 s | 38.59 s (-2.3% better) |
| reload_wall_s | 1.51 s | 1.63 s (+7.8% worse) |
| worldgen_columns_per_s | 42.55 columns/s | 43.56 columns/s (+2.4% better) |
| worldgen_cpu_s | 45.92 s | 44.49 s (-3.1% better) |
| idle_tick_mean_ms | 1.62 ms | 1.38 ms (-15.1% better) |
| idle_tick_median_ms | 1.39 ms | 1.20 ms (-14.2% better) |
| idle_tick_p95_ms | 3.00 ms | 2.42 ms (-19.1% better) |
| idle_tick_p99_ms | 5.90 ms | 4.24 ms (-28.1% better) |
| idle_tick_max_ms | 11.71 ms | 8.35 ms (-28.6% better) |
| entities_tick_mean_ms | 5.44 ms | 3.36 ms (-38.1% better) |
| entities_tick_median_ms | 4.51 ms | 2.92 ms (-35.3% better) |
| entities_tick_p95_ms | 9.10 ms | 5.29 ms (-41.8% better) |
| entities_tick_p99_ms | 18.67 ms | 8.60 ms (-53.9% better) |
| entities_tick_max_ms | 150.13 ms | 148.95 ms (-0.8%) |
| peak_working_set_mb | 1,837.25 MB | 1,840.31 MB (+0.2%) |
| heap_after_worldgen_mb | 1,250.90 MB | 1,232.10 MB (-1.5%) |
| heap_after_entities_mb | 1,161.53 MB | 1,136.40 MB (-2.2% better) |
| peak_working_set_reload_mb | 1,478.84 MB | 1,522.05 MB (+2.9% worse) |
| worldgen_cpu_ms | 45,916.12 ms | 44,494.12 ms (-3.1% better) |
| worldgen_gc_pause_ms | 1,064.99 ms | 968.80 ms (-9.0% better) |
| worldgen_gc_gen0 | 361.00 gen0 | 274.50 gen0 (-24.0% better) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 1,567.91 ms | 1,406.18 ms (-10.3% better) |
| idle_gc_pause_ms | 67.02 ms | 41.38 ms (-38.3% better) |
| idle_gc_gen0 | 16.00 gen0 | 15.00 gen0 (-6.2% better) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) |
| entities_cpu_ms | 10,364.37 ms | 6,440.80 ms (-37.9% better) |
| entities_gc_pause_ms | 344.79 ms | 197.67 ms (-42.7% better) |
| entities_gc_gen0 | 82.00 gen0 | 54.00 gen0 (-34.1% better) |
| entities_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) |
| idle_cpu_pct_of_one_core | 7.80 % | 6.99 % (-10.4% better) |
| entities_cpu_pct_of_one_core | 23.05 % | 14.32 % (-37.9% better) |
| idle_tps | 29.84 ticks/s | 29.82 ticks/s (-0.1%) |
| entities_tps | 29.81 ticks/s | 29.81 ticks/s (+0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |