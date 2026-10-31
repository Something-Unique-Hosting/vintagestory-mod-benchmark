| Metric | Vanilla 1.22.7, no mods | Synergy 1.1.25 (vs baseline) | Synergy, activation range off (vs baseline) |
|---|---|---|---|
| startup_fresh_s | 15.76 s | 16.96 s (+7.6% worse) | 15.88 s (+0.8%) |
| worldgen_wall_s | 40.08 s | 40.05 s (-0.1%) | 40.34 s (+0.6%) |
| worldgen_columns_per_s | 41.94 columns/s | 41.97 columns/s (+0.1%) | 41.67 columns/s (-0.6%) |
| worldgen_cpu_s | 46.87 s | 46.78 s (-0.2%) | 47.39 s (+1.1%) |
| idle_tick_mean_ms | 2.18 ms | 2.35 ms (+8.2% worse) | 2.27 ms (+4.3% worse) |
| idle_tick_median_ms | 2.08 ms | 2.35 ms (+13.1% worse) | 2.18 ms (+5.0% worse) |
| idle_tick_p95_ms | 3.20 ms | 3.19 ms (-0.2%) | 3.17 ms (-1.0%) |
| idle_tick_p99_ms | 5.68 ms | 5.59 ms (-1.6%) | 5.18 ms (-8.9% better) |
| idle_tick_max_ms | 11.23 ms | 9.58 ms (-14.7% better) | 11.63 ms (+3.5% worse) |
| entities_tick_mean_ms | 6.75 ms | 5.19 ms (-23.0% better) | 6.40 ms (-5.1% better) |
| entities_tick_median_ms | 5.91 ms | 4.79 ms (-18.9% better) | 5.85 ms (-1.1%) |
| entities_tick_p95_ms | 10.40 ms | 6.85 ms (-34.1% better) | 9.88 ms (-5.0% better) |
| entities_tick_p99_ms | 19.60 ms | 10.37 ms (-47.1% better) | 17.59 ms (-10.2% better) |
| entities_tick_max_ms | 162.39 ms | 154.86 ms (-4.6% better) | 166.83 ms (+2.7% worse) |
| peak_working_set_mb | 1,829.71 MB | 1,852.53 MB (+1.2%) | 1,877.77 MB (+2.6% worse) |
| heap_after_worldgen_mb | 1,249.53 MB | 1,234.28 MB (-1.2%) | 1,223.84 MB (-2.1% better) |
| heap_after_entities_mb | 1,160.30 MB | 1,324.09 MB (+14.1% worse) | 1,348.84 MB (+16.2% worse) |
| worldgen_cpu_ms | 46,869.44 ms | 46,779.94 ms (-0.2%) | 47,392.64 ms (+1.1%) |
| worldgen_gc_pause_ms | 1,161.51 ms | 1,110.89 ms (-4.4% better) | 1,094.12 ms (-5.8% better) |
| worldgen_gc_gen0 | 361.00 gen0 | 360.00 gen0 (-0.3%) | 361.00 gen0 (+0.0%) |
| worldgen_gc_gen2 | 1.00 gen2 | 1.00 gen2 (+0.0%) | 1.00 gen2 (+0.0%) |
| idle_cpu_ms | 2,047.05 ms | 2,031.60 ms (-0.8%) | 1,995.90 ms (-2.5% better) |
| idle_gc_pause_ms | 62.19 ms | 53.75 ms (-13.6% better) | 53.47 ms (-14.0% better) |
| idle_gc_gen0 | 16.00 gen0 | 16.00 gen0 (+0.0%) | 16.00 gen0 (+0.0%) |
| idle_gc_gen2 | 0.00 gen2 | 0.00 gen2 (+nan% worse) | 0.00 gen2 (+nan% worse) |
| entities_cpu_ms | 12,385.54 ms | 8,626.25 ms (-30.4% better) | 11,085.77 ms (-10.5% better) |
| entities_gc_pause_ms | 355.93 ms | 206.69 ms (-41.9% better) | 285.87 ms (-19.7% better) |
| entities_gc_gen0 | 87.00 gen0 | 52.00 gen0 (-40.2% better) | 70.00 gen0 (-19.5% better) |
| entities_gc_gen2 | 1.00 gen2 | 0.00 gen2 (-100.0% better) | 0.00 gen2 (-100.0% better) |
| idle_cpu_pct_of_one_core | 10.16 % | 10.10 % (-0.6%) | 9.92 % (-2.4% better) |
| entities_cpu_pct_of_one_core | 27.55 % | 19.19 % (-30.3% better) | 24.68 % (-10.4% better) |
| idle_tps | 29.79 ticks/s | 29.82 ticks/s (+0.1%) | 29.81 ticks/s (+0.1%) |
| entities_tps | 29.79 ticks/s | 29.77 ticks/s (-0.1%) | 29.81 ticks/s (+0.0%) |

| Mod | Version tested | Author | Mod DB |
|---|---|---|---|
| Synergy | 1.1.25 | Zaldaryon | [synergy](https://mods.vintagestory.at/synergy) |
| Tungsten | 1.3.7 | Zaldaryon | [tungsten](https://mods.vintagestory.at/tungsten) |