| Metric | Vanilla 1.22.7, no mods | Synergy 1.1.25 (vs baseline) | Tungsten 1.3.7 (vs baseline) | All 2 mods together (vs baseline) |
|---|---|---|---|---|
| startup_fresh_s | 15.81 s | 15.64 s (-1.1%) | 16.23 s (+2.7% worse) | 15.71 s (-0.6%) |
| startup_existing_s | 10.74 s | 11.20 s (+4.3% worse) | 11.78 s (+9.7% worse) | 11.28 s (+5.0% worse) |
| worldgen_wall_s | 39.50 s | 38.86 s (-1.6%) | 38.72 s (-2.0%) | 38.59 s (-2.3% better) |
| reload_wall_s | 1.51 s | 1.47 s (-2.9% better) | 1.61 s (+6.8% worse) | 1.63 s (+7.8% worse) |
| worldgen_columns_per_s | 42.55 columns/s | 43.25 columns/s (+1.6%) | 43.41 columns/s (+2.0% better) | 43.56 columns/s (+2.4% better) |
| worldgen_cpu_s | 45.92 s | 44.66 s (-2.7% better) | 44.84 s (-2.4% better) | 44.49 s (-3.1% better) |
| idle_tick_mean_ms | 1.62 ms | 1.35 ms (-16.9% better) | 1.52 ms (-6.5% better) | 1.38 ms (-15.1% better) |
| idle_tick_median_ms | 1.39 ms | 1.17 ms (-16.3% better) | 1.36 ms (-2.4% better) | 1.20 ms (-14.2% better) |
| idle_tick_p95_ms | 3.00 ms | 2.57 ms (-14.3% better) | 2.66 ms (-11.2% better) | 2.42 ms (-19.1% better) |
| idle_tick_p99_ms | 5.90 ms | 4.70 ms (-20.3% better) | 4.95 ms (-16.0% better) | 4.24 ms (-28.1% better) |
| idle_tick_max_ms | 11.71 ms | 8.09 ms (-30.9% better) | 9.66 ms (-17.5% better) | 8.35 ms (-28.6% better) |
| entities_tick_mean_ms | 5.44 ms | 3.36 ms (-38.1% better) | 4.67 ms (-14.2% better) | 3.36 ms (-38.1% better) |
| entities_tick_median_ms | 4.51 ms | 2.89 ms (-36.1% better) | 3.99 ms (-11.6% better) | 2.92 ms (-35.3% better) |
| entities_tick_p95_ms | 9.10 ms | 5.24 ms (-42.4% better) | 7.95 ms (-12.6% better) | 5.29 ms (-41.8% better) |
| entities_tick_p99_ms | 18.67 ms | 9.11 ms (-51.2% better) | 17.68 ms (-5.3% better) | 8.60 ms (-53.9% better) |
| entities_tick_max_ms | 150.13 ms | 147.39 ms (-1.8%) | 147.54 ms (-1.7%) | 148.95 ms (-0.8%) |
| peak_working_set_mb | 1,837.25 MB | 1,844.13 MB (+0.4%) | 1,850.02 MB (+0.7%) | 1,840.31 MB (+0.2%) |
| heap_after_worldgen_mb | 1,250.90 MB | 1,237.45 MB (-1.1%) | 1,242.63 MB (-0.7%) | 1,232.10 MB (-1.5%) |
| heap_after_entities_mb | 1,161.53 MB | 1,142.11 MB (-1.7%) | 1,150.76 MB (-0.9%) | 1,136.40 MB (-2.2% better) |
| peak_working_set_reload_mb | 1,478.84 MB | 1,486.13 MB (+0.5%) | 1,518.23 MB (+2.7% worse) | 1,522.05 MB (+2.9% worse) |
| worldgen_cpu_ms | 45,916.12 ms | 44,661.61 ms (-2.7% better) | 44,835.32 ms (-2.4% better) | 44,494.12 ms (-3.1% better) |
| worldgen_gc_pause_ms | 1,064.99 ms | 1,037.67 ms (-2.6% better) | 1,005.71 ms (-5.6% better) | 968.80 ms (-9.0% better) |
| worldgen_gc_gen0 | 361.00 gen0 | 359.00 gen0 (-0.6%) | 276.00 gen0 (-23.5% better) | 274.50 gen0 (-24.0% better) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 1,567.91 ms | 1,448.40 ms (-7.6% better) | 1,516.31 ms (-3.3% better) | 1,406.18 ms (-10.3% better) |
| idle_gc_pause_ms | 67.02 ms | 49.50 ms (-26.1% better) | 55.04 ms (-17.9% better) | 41.38 ms (-38.3% better) |
| idle_gc_gen0 | 16.00 gen0 | 16.00 gen0 (+0.0%) | 15.50 gen0 (-3.1% better) | 15.00 gen0 (-6.2% better) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) | 0.00 gen2 (+nan% worse) | 0.00 gen2 (+nan% worse) |
| entities_cpu_ms | 10,364.37 ms | 6,622.89 ms (-36.1% better) | 9,061.31 ms (-12.6% better) | 6,440.80 ms (-37.9% better) |
| entities_gc_pause_ms | 344.79 ms | 210.17 ms (-39.0% better) | 332.52 ms (-3.6% better) | 197.67 ms (-42.7% better) |
| entities_gc_gen0 | 82.00 gen0 | 52.50 gen0 (-36.0% better) | 79.50 gen0 (-3.0% better) | 54.00 gen0 (-34.1% better) |
| entities_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) |
| idle_cpu_pct_of_one_core | 7.80 % | 7.20 % (-7.7% better) | 7.55 % (-3.3% better) | 6.99 % (-10.4% better) |
| entities_cpu_pct_of_one_core | 23.05 % | 14.73 % (-36.1% better) | 20.16 % (-12.6% better) | 14.32 % (-37.9% better) |
| idle_tps | 29.84 ticks/s | 29.82 ticks/s (-0.1%) | 29.85 ticks/s (+0.0%) | 29.82 ticks/s (-0.1%) |
| entities_tps | 29.81 ticks/s | 29.80 ticks/s (-0.0%) | 29.82 ticks/s (+0.0%) | 29.81 ticks/s (+0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |