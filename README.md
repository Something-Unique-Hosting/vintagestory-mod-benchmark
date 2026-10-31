# Vintage Story mod benchmark

The numbers behind our blog post *Synergy and Tungsten on a Vintage Story Server: We Benchmarked Both, Alone and Together (1.22.7)* are in [`results/`](results/) and the charts in [`charts/`](charts/).

A repeatable, player-free benchmark that measures what individual mods, and a collection of them, cost a
Vintage Story dedicated server. One official server build, N mod sets, same world seed, same phases, run
inside an ordinary hosted game server so the numbers are what a customer would see.

It grew out of our [Stratum vs vanilla benchmark](https://github.com/Something-Unique-Hosting/vintagestory-stratum-benchmark)
and keeps its method (worldgen, idle, creature load, optional load ladder; every main-thread tick timed through a
Harmony hook) and adds what a mod comparison needs:

- **Mod sets as variants.** `baseline` (no mods), one variant per mod, and `all` (the collection), each run on a
  fresh world with a fixed seed. Order alternates between runs so node noise hits every set equally.
- **Startup phases.** Timestamps of the server run phases, so asset-heavy mods show up as "where startup time goes".
- **Per-mod attribution.** Every game-tick listener (including block entities) and every entity behaviour a mod
  declares is timed and credited to that mod. What a mod does through Harmony patches of game code or through
  JSON-only content is *not* separable; it shows up in the totals only.
- **Placed blocks.** `PLACE="primitivesurvival:fishbasket-north=40,..."` sets that many of a block around spawn
  before the idle phase, so mods whose cost lives in block entities have something to tick. Codes the current
  variant does not know are skipped, so one setting fits every variant.
- **A player, when the mods need one.** `BOT=1` starts a headless bot client (`bot/`, speaks the game's join
  handshake and answers pings, never moves) that joins each server before measuring, so distance-to-player logic in
  mods and in the game itself is exercised. The server listens on 127.0.0.1 only and `VerifyPlayerAuth` is off in
  the bench config, so the bot needs no game account. `SPAWN_RANGE` (blocks around spawn) and `ALWAYS_ACTIVE=0`
  shape the creature load around that player instead of forcing every creature active across the loaded area.
- **Sum of parts.** The collection's measured cost is charted against the sum of the single-mod costs.
- **Loaded mod list** with versions in every result, and a lock file with the exact mod DB release used.

## Layout

```
mod/          the benchmark mod (SuhBench.csproj, BenchModSystem.cs, modinfo.json; modid suhbench)
bot/          headless bot client (VSBot.csproj, Program.cs) used by BOT=1
nonet/        .NET startup hook that stops the server opening listen sockets (hermetic, no clients)
harness/      serverconfig.bench.json (seed 20261030, three ModPaths), variants.example.json
tools/        fetch_mods.py, analyze_mods.py, make_post.py, build_html.py
container/    run_in_container.sh
mods/         fetch_mods.py output: pool/*.zip, sets/<variant>.list, variants.txt, variants.lock.json
results/      raw per-run JSON, server and bot logs from our runs (ny8-synergy-tungsten-noplayer, -player, -ladder)
charts/       the PNG charts and summary tables generated from results/
```

## 1. Pick the mods

Copy `harness/variants.example.json` to `harness/variants.json` and list the mods by their mod DB URL alias
(the slug in `https://mods.vintagestory.at/<slug>`). Optional per mod: `version` to pin a release, `deps` for
library mods that must load with it, `library: true` to exclude a mod from getting its own variant, `file` for a
local zip. Without a `variants` list you get `baseline`, one variant per non-library mod, and `all`. An explicit
variant may carry `config: {"Synergy.json": {...}}`: the files land in the run's `ModConfig/` folder, so the same
mod can be tested with different settings as separate variants.

```bash
python3 tools/fetch_mods.py harness/variants.json          # resolves newest release for the game version, downloads, writes mods/
```

## 2. Build

```bash
export DOTNET_ROOT=$HOME/.dotnet PATH=$HOME/.dotnet:$PATH   # .NET 10 SDK
dotnet build mod   -c Release -p:VS_SERVER=<official server dir> -p:OutputPath=$PWD/build/suhbench/
dotnet build nonet -c Release -p:VS_SERVER=<official server dir> -p:OutputPath=$PWD/build/nonet/
dotnet build bot   -c Release -p:VS_SERVER=<official server dir> -p:OutputPath=$PWD/build/bot/
mkdir -p bench/mod bench/nonet && cp -r build/suhbench bench/mod/ && cp build/nonet/NoNetHook.dll bench/nonet/ && cp -r build/bot bench/bot && cp harness/serverconfig.bench.json tools/run_in_container.sh bench/
```

## 3. Run

**Locally** (smoke test or a desktop number; not for publication):

```bash
BENCH_HOME=$PWD VS_SERVER=<official server dir> OUT=results/local DATA=/tmp/benchdata HOLD=0 \
  RUNS=1 RADIUS=6 SETTLE=5 IDLE=10 ENTITIES=100 ENTITY_SEC=15 bash bench/run_in_container.sh
```

**In a game-server container** (Pterodactyl, Pelican, Calagopus; this is how the published numbers were made):
upload `bench/` (mod, hook, bot, config, runner) and `mods/` to the server's volume next to `servers/vanilla` (the
official Linux server build), then set the startup command to

```
BENCH_DIR=/home/container/bench MODS_DIR=/home/container/mods OUT=/home/container/results \
RUNS=4 RADIUS=20 ENTITIES=500 [BOT=1 SPAWN_RANGE=96 ALWAYS_ACTIVE=0] [LADDER=1000,2000,4000 MODES=gen] \
bash /home/container/bench/run_in_container.sh
```

Results land in `/home/container/results/`. The runner prints `BENCH DONE` and then holds the container open, because
Wings restarts a server on any exit; stop it from the panel and download the folder. Runner knobs: `RUNS RADIUS IDLE
SETTLE ENTITIES ENTITY_SEC VARIANTS MODES TIMEOUT LADDER STEP_SEC PLACE CREATURES BOT BOT_VIEW PORT SPAWN_RANGE
ALWAYS_ACTIVE HOLD`. Wings attaches a TTY, so the game is started with `timeout --foreground` and stdin from `/dev/null`;
the image has no NuGet access, so everything ships as files.

Timing: one gen+load pair at radius 20 with 500 creatures is about 3.5 minutes in a 4-core container, so
`variants × runs × 3.5 min`: 4 variants × 4 runs is about one hour, 8 variants about two.

## 4. Analyse, draft, build the page

```bash
python3 tools/analyze_mods.py --results results/ny8-mods --out charts/ny8-mods --tag "(NY 8, 4 cores / 6 GB)" --dark
python3 tools/make_post.py --charts charts/ny8-mods --results results/ny8-mods --out blog/post.md --node "NY 8 (Ryzen 9 9950X), 4 cores / 6 GB"
mkdir -p blog/images && cp charts/ny8-mods/*.png blog/images/
python3 tools/build_html.py blog/post.md blog/images blog/post.html --design classic
```

`analyze_mods.py` writes charts 01-19 (startup, startup phases, worldgen, tick at idle and under load, CDF,
memory, GC, CPU, TPS, overhead-vs-baseline small multiples, sum of parts, per-mod attribution, per-system
breakdown, timeline, ladder), `summary.json` (every metric per variant with change vs baseline), `summary.md`
and `mods.md`. It reads `variants.lock.json` from the results folder for labels and versions (the runner copies it
there). `--exclude <variant>-run<n>` drops a bad run.

`make_post.py` turns that into a Markdown draft in the same shape as the Stratum post: front matter with
title, description, keywords and a four-tile KPI strip (`kpi1..kpi4: "value | label | note | good|cost"`), the
short version, the mod table, method, one section per chart with its numbers table, caveats, reproduce. Every
number comes from `summary.json`; every `TODO` is a sentence the author writes. `build_html.py` renders the
Markdown plus inlined PNGs into one standalone page (`--design classic` matches the Stratum post).

## Result file

One JSON per run, same schema as the Stratum benchmark plus: `variant`, `game_version`, `mods[]` (modid, name,
version, file, builtin), `mods_under_test[]`, `run_phases_ms{}`, `placed_blocks{}`, and per phase `mods_ms{}`
(`<modid>/listeners`, `<modid>/behaviours`: total_ms, calls, max_ms) and `listener_types_ms{}` (top 25 handler
types, diagnostic); with `BOT=1` also `players_online_at_start`, `player_names`, `spawn_range`, `creatures_always_active`. The benchmark's own 250 ms sampler appears as `suhbench/listeners` and is excluded from the
attribution chart.

## Caveats to keep in the post

- No players: nothing per player (packets, inventories, GUIs, commands) is measured.
- Fresh world, nothing built unless `PLACE` is used; block-entity-heavy mods are undercounted otherwise.
- Creatures forced active is harsher than a live server.
- Default mod configs. One node, one plan size: relative costs transfer, absolute numbers do not.
- A mod that Harmony-patches worldgen or entity code is measured in the totals but cannot be attributed.

## License

MIT. Vintage Story and the mods are not included; download them from their own sites. Something Unique Hosting is not
affiliated with the mods' author.
