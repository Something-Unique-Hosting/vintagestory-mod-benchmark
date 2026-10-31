#!/bin/bash
# Mod-set benchmark runner. Runs as the panel server's startup command inside the dotnet_10 yolk image (no
# python/jq needed), or locally with BENCH_HOME pointed at a checkout. One server build (vanilla), N mod sets.
# For each run r and each variant v (order alternates forward/reverse per run so drift hits every set equally):
#   gen : fresh world, fixed seed, the variant's mods from mods/sets/<v>.list copied to mods/sets/<v>/
#   load: restart on the world the gen run made and reload the same columns from disk
# Results land in $OUT as <variant>-run<r>-<mode>.json (+ stdout and server-main logs).
#   env knobs: RUNS RADIUS IDLE SETTLE ENTITIES ENTITY_SEC VARIANTS MODES TIMEOUT LADDER STEP_SEC CREATURES HOLD
set -u
H=${BENCH_HOME:-/home/container}
B=${BENCH_DIR:-$H/bench}                  # mod/suhbench/, nonet/NoNetHook.dll, serverconfig.bench.json
VS_SERVER=${VS_SERVER:-$H/servers/vanilla}
MODS=${MODS_DIR:-$H/mods}                 # pool/*.zip, sets/<variant>.list, variants.txt
OUT=${OUT:-$H/results}; DATA=${DATA:-$H/benchdata}
RUNS=${RUNS:-4}; RADIUS=${RADIUS:-20}; IDLE=${IDLE:-20}; SETTLE=${SETTLE:-20}
ENTITIES=${ENTITIES:-500}; ENTITY_SEC=${ENTITY_SEC:-45}; MODES=${MODES:-gen,load}
VARIANTS=${VARIANTS:-$(tr -d '\n' < "$MODS/variants.txt" 2>/dev/null)}
TIMEOUT=${TIMEOUT:-1500}; HOLD=${HOLD:-1}
LADDER=${LADDER:-}; STEP_SEC=${STEP_SEC:-30}; SPAWN_PER_TICK=${SPAWN_PER_TICK:-250}; LADDER_STOP_MS=${LADDER_STOP_MS:-150}
CREATURES=${CREATURES:-}                  # optional comma list of entity codes to spawn (default: the mod's vanilla mix)
PLACE=${PLACE:-}                          # optional "domain:block=count,..." placed before the idle phase (see BENCH_PLACE in the mod)
BOT=${BOT:-0}; BOT_VIEW=${BOT_VIEW:-128}  # BOT=1: a headless bot client joins each server before measuring (server listens on 127.0.0.1:$PORT)
PORT=${PORT:-42777}
SPAWN_RANGE=${SPAWN_RANGE:-}; ALWAYS_ACTIVE=${ALWAYS_ACTIVE:-1}   # creature spawn half-width in blocks (default: loaded area); 0 = let distance activation apply
mkdir -p "$OUT" "$DATA"
[ -z "$VARIANTS" ] && { echo "no VARIANTS and no $MODS/variants.txt"; exit 2; }

{
  echo "date: $(date -u +%FT%TZ)"; echo "host: $(hostname)"; echo "nproc: $(nproc)"
  echo "cgroup memory.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null)"
  echo "cgroup cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null)"
  echo "dotnet: $(dotnet --version 2>/dev/null)"; grep -m1 'model name' /proc/cpuinfo; grep -E 'MemTotal|MemAvailable' /proc/meminfo
  echo "SERVER_MEMORY=${SERVER_MEMORY:-?} P_SERVER_UUID=${P_SERVER_UUID:-?}"
  echo "variants: $VARIANTS"; echo "modes: $MODES runs: $RUNS radius: $RADIUS entities: $ENTITIES ladder: $LADDER place: $PLACE bot: $BOT spawn_range: $SPAWN_RANGE always_active: $ALWAYS_ACTIVE"
} | tee "$OUT/env.txt"
[ -f "$MODS/variants.lock.json" ] && cp "$MODS/variants.lock.json" "$OUT/variants.lock.json"

# assemble each variant's mod folder from its list (pool files are shared, lists are tiny)
IFS=, read -ra VS <<< "$VARIANTS"
for v in "${VS[@]}"; do
  d="$MODS/sets/$v"; rm -rf "$d"; mkdir -p "$d"
  if [ -f "$MODS/sets/$v.list" ]; then
    while IFS= read -r f; do [ -n "$f" ] && cp "$MODS/pool/$f" "$d/"; done < "$MODS/sets/$v.list"
  elif [ "$v" != baseline ]; then echo "WARNING: no $MODS/sets/$v.list, variant $v runs without mods"; fi
  echo "variant $v: $(ls "$d" | tr '\n' ' ')"
done

write_cfg() { # $1 datapath $2 worldname $3 variant
  mkdir -p "$1/Saves"
  if [ -d "$MODS/sets/$3.config" ]; then mkdir -p "$1/ModConfig"; cp "$MODS/sets/$3.config"/* "$1/ModConfig/"; echo "   mod config for $3: $(ls "$MODS/sets/$3.config" | tr '\n' ' ')"; fi
  sed -e "s#__SAVE__#$1/Saves/bench.vcdbs#" -e "s#__WORLD__#$2#" -e "s#__MODDIR__#$B/mod#" -e "s#__VARMODS__#$MODS/sets/$3#" "$B/serverconfig.bench.json" > "$1/serverconfig.json"
}

run_one() { # variant run mode
  local v=$1 r=$2 m=$3 dp="$DATA/$1-$2" out="$OUT/$1-run$2-$3.json"
  if [ "$m" = gen ]; then rm -rf "$dp"; write_cfg "$dp" "bench-$v-$r" "$v"; fi
  local idle=$IDLE ents=$ENTITIES
  [ "$m" = load ] && { idle=10; ents=0; }
  echo "[$(date +%T)] $v run $r mode=$m -> $(basename "$out")"
  local t0=$SECONDS nonet=1 botpid=
  [ "$BOT" = 1 ] && nonet=0
  ( cd "$VS_SERVER" && env BENCH_LABEL="$v" BENCH_MODE="$m" BENCH_OUT="$out" BENCH_RADIUS="$RADIUS" BENCH_IDLE_SEC="$idle" \
      BENCH_SETTLE_SEC="$SETTLE" BENCH_ENTITIES="$ents" BENCH_ENTITY_SEC="$ENTITY_SEC" BENCH_SYSTIMING=1 BENCH_MODTIMING=1 BENCH_NONET=$nonet BENCH_WAIT_PLAYER=$BOT \
      BENCH_CREATURES="$CREATURES" BENCH_PLACE="$PLACE" BENCH_SPAWN_RANGE="$SPAWN_RANGE" BENCH_ALWAYS_ACTIVE="$ALWAYS_ACTIVE" \
      BENCH_LADDER="$([ "$m" = gen ] && echo "$LADDER")" BENCH_STEP_SEC="$STEP_SEC" BENCH_SPAWN_PER_TICK="$SPAWN_PER_TICK" BENCH_LADDER_STOP_MS="$LADDER_STOP_MS" \
      DOTNET_TieredPGO=1 DOTNET_STARTUP_HOOKS="$B/nonet/NoNetHook.dll" \
      timeout --foreground "$TIMEOUT" dotnet VintagestoryServer.dll --dataPath "$dp" < /dev/null > "${out%.json}.stdout.log" 2>&1 ) &
  local srvpid=$!
  # --foreground + stdin from /dev/null: Wings attaches a TTY, and a background process group touching it gets SIGTTIN and stops.
  if [ "$BOT" = 1 ]; then
    # the bot retries the connection until the server listens, joins, then idles at spawn answering pings until killed
    ( env VS_SERVER="$VS_SERVER" timeout --foreground "$TIMEOUT" dotnet "$B/bot/VSBot.dll" --host 127.0.0.1 --port "$PORT" --name SUHBenchBot --view "$BOT_VIEW" --retry 240 < /dev/null > "${out%.json}.bot.log" 2>&1 ) &
    botpid=$!
  fi
  wait "$srvpid"; local rc=$?
  [ -n "$botpid" ] && { kill "$botpid" 2>/dev/null; wait "$botpid" 2>/dev/null; }
  [ -f "$dp/Logs/server-main.log" ] && cp "$dp/Logs/server-main.log" "${out%.json}.server-main.log"
  local ok=MISSING; [ -f "$out" ] && ok=ok
  echo "   exit=$rc elapsed=$((SECONDS - t0))s result=$ok"
  echo "{\"variant\":\"$v\",\"run\":$r,\"mode\":\"$m\",\"rc\":$rc,\"elapsed_s\":$((SECONDS - t0)),\"ok\":\"$ok\"}" >> "$OUT/runs.jsonl"
}

IFS=, read -ra MS <<< "$MODES"
for ((r = 1; r <= RUNS; r++)); do
  if (( r % 2 == 1 )); then order=("${VS[@]}"); else order=(); for ((i = ${#VS[@]} - 1; i >= 0; i--)); do order+=("${VS[i]}"); done; fi
  for v in "${order[@]}"; do for m in "${MS[@]}"; do run_one "$v" "$r" "$m"; done; done
done
echo "BENCH DONE $(date -u +%FT%TZ)"; touch "$OUT/DONE"
# In a Wings container any exit (even 0) is a crash and restarts the server, which would rerun the benchmark and
# overwrite the results. Hold the container open; stop the server from the panel once the results are fetched.
if [ "$HOLD" = 1 ]; then echo "holding container open; stop the server from the panel"; sleep infinity; fi
