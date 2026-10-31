#!/usr/bin/env python3
"""Draft the blog post from the analyzer output. Every number in the draft comes from summary.json; prose
placeholders are marked TODO for the author to replace. Re-run after re-analysing; edit the Markdown after.

  python3 tools/make_post.py --charts charts/ny8-mods --results results/ny8-mods --out blog/post.md
         [--title "..."] [--node "NY 8 (Ryzen 9 9950X), 4 cores / 6 GB"] [--date 2026-11-02]
"""
import argparse, datetime, json, pathlib, re

def fmt(x, unit):
    if x is None or x != x: return "n/a"
    if unit == "s": return f"{x:,.1f} s"
    if unit == "ms": return f"{x:,.2f} ms"
    if unit == "MB": return f"{x:,.0f} MB"
    if unit == "%": return f"{x:,.0f}%"
    if unit == "ticks/s": return f"{x:,.1f}"
    if unit == "columns/s": return f"{x:,.1f}"
    return f"{x:,.2f} {unit}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--charts", required=True); ap.add_argument("--results", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--title", default=None); ap.add_argument("--node", default=None); ap.add_argument("--date", default=str(datetime.date.today()))
    ap.add_argument("--images", default="images", help="image path prefix used in the Markdown")
    ap.add_argument("--repo", default="https://github.com/Something-Unique-Hosting/vintagestory-mod-benchmark")
    ap.add_argument("--scenario-b", default=None, help="charts dir of a second pass (e.g. with a player online)")
    ap.add_argument("--scenario-b-label", default="With one player online"); ap.add_argument("--scenario-b-images", default="images-b")
    ap.add_argument("--scenario-a-label", default="Empty server, no players")
    a = ap.parse_args()
    ch = pathlib.Path(a.charts); res = pathlib.Path(a.results)
    S = json.loads((ch / "summary.json").read_text()); M = S["metrics"]
    base = S["baseline"]; coll = S.get("collection"); V = [v["id"] for v in S["variants"]]; L = {v["id"]: v["label"] for v in S["variants"]}
    singles = [v for v in V if v not in (base, coll)]
    game = S.get("game_version")
    env = (res / "env.txt").read_text() if (res / "env.txt").exists() else ""
    cpu = re.search(r"model name\s*:\s*(.*)", env); nproc = re.search(r"nproc: (\d+)", env); memmax = re.search(r"memory.max: (\d+)", env); cpumax = re.search(r"cpu.max: (\d+) (\d+)", env)
    cores = f"{int(cpumax.group(1)) / int(cpumax.group(2)):g}" if cpumax else (nproc.group(1) if nproc else "?")
    mem_gb = f"{int(memmax.group(1)) / 2**30:.0f} GB" if memmax else "?"
    node = a.node or f"{cpu.group(1).strip() if cpu else 'unknown CPU'}, {cores} cores / {mem_gb}"
    runs_gen = max(S["runs"].get(f"{v}/gen", 0) for v in V); runs_load = max(S["runs"].get(f"{v}/load", 0) for v in V)
    cols = M["worldgen_wall_s"]; ents = re.search(r"Mean tick, (\d+)", json.dumps(S)) 
    ents_n = next((int(k.split("_")[1]) for k in M if k.startswith("ladder_")), None)
    nmods = len(singles)

    def row(name, label, MM=None):
        m = (MM or M).get(name)
        if not m or base not in m: return None
        cells = [fmt(m[base]["median"], m["unit"])]
        for v in V[1:]:
            x = m.get(v, {}).get("median"); c = m["change_pct"].get(v)
            cells.append(fmt(x, m["unit"]) + (f" ({c:+.0f}%)" if c is not None and c == c and abs(c) >= 1 else ""))
        return f"| {label} | " + " | ".join(cells) + " |"
    def table(rows, first="Metric"):
        head = f"| {first} | " + " | ".join(L[v] for v in V) + " |\n|---|" + "---|" * len(V)
        return head + "\n" + "\n".join(r for r in rows if r)
    def delta(name, v, unit=None):
        m = M.get(name); 
        if not m or v not in m.get("delta", {}): return "n/a"
        d = m["delta"][v]; c = m["change_pct"][v]
        return f"{fmt(d, unit or m['unit']).replace(' ', ' ')} ({c:+.0f}%)" if d == d else "n/a"
    def signed(name, v):
        m = M.get(name); d = m["delta"][v]; u = m["unit"]
        s = fmt(abs(d), u); return ("+" if d >= 0 else "-") + s

    focus = coll or (singles[0] if singles else None)
    title = a.title or (f"We Benchmarked {nmods} Vintage Story Mods on a Real Server: What Each One Costs ({game or ''})".replace(" ()", "") if nmods > 1 else f"What {L[focus]} Costs Your Vintage Story Server: A Benchmark")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    desc = (f"We measured what {nmods} popular Vintage Story mods cost a dedicated server, one at a time and all together, inside a real hosted game server: "
            f"startup time, world generation, idle and creature tick time, memory and garbage collection. Charts, numbers and a reproducible method.")
    kpis = []
    if focus:
        kpis.append(f'kpi1: "{signed("idle_tick_mean_ms", focus)} | idle tick, {L[focus]} | {fmt(M["idle_tick_mean_ms"][base]["median"], "ms")} -> {fmt(M["idle_tick_mean_ms"][focus]["median"], "ms")} | {"cost" if M["idle_tick_mean_ms"]["delta"][focus] > 0 else "good"}"')
        if "entities_tick_mean_ms" in M: kpis.append(f'kpi2: "{signed("entities_tick_mean_ms", focus)} | mean tick under creature load | {fmt(M["entities_tick_mean_ms"][base]["median"], "ms")} -> {fmt(M["entities_tick_mean_ms"][focus]["median"], "ms")} | {"cost" if M["entities_tick_mean_ms"]["delta"][focus] > 0 else "good"}"')
        kpis.append(f'kpi3: "{signed("startup_fresh_s", focus)} | startup time | {fmt(M["startup_fresh_s"][base]["median"], "s")} -> {fmt(M["startup_fresh_s"][focus]["median"], "s")} | {"cost" if M["startup_fresh_s"]["delta"][focus] > 0 else "good"}"')
        kpis.append(f'kpi4: "{signed("peak_working_set_mb", focus)} | peak memory | {fmt(M["peak_working_set_mb"][base]["median"], "MB")} -> {fmt(M["peak_working_set_mb"][focus]["median"], "MB")} | {"cost" if M["peak_working_set_mb"]["delta"][focus] > 0 else "good"}"')

    o = []
    o.append("---"); o.append(f'title: "{title}"'); o.append(f"slug: {slug}"); o.append(f'description: "{desc}"')
    o.append("keywords: Vintage Story mods, Vintage Story server performance, Vintage Story mod lag, Vintage Story dedicated server, Vintage Story server hosting, Vintage Story TPS, " + ", ".join(L[v] for v in singles))
    o.append(f"date: {a.date}"); o.append("author: Something Unique Hosting"); o.append(f"repo: {a.repo}"); o += kpis; o.append("---\n")
    o.append(f"# {title}\n")
    o.append(f"TODO intro. Every Vintage Story server owner asks the same question before installing a mod: what will it cost me? We run a lot of Vintage Story servers, so we built a repeatable, player-free benchmark and ran it inside an ordinary hosted game server on one of our production nodes ({node}). We measured the unmodded {game or ''} server, then each of {nmods} mods on its own, then all of them together. This is what we found.\n")
    o.append("## The short version\n")
    for v in singles:
        o.append(f"- **{L[v]}**: idle tick {delta('idle_tick_mean_ms', v)}, mean tick under creature load {delta('entities_tick_mean_ms', v)}, startup {delta('startup_fresh_s', v)}, world generation {delta('worldgen_wall_s', v)}, peak memory {delta('peak_working_set_mb', v)}. TODO one-line verdict.")
    if coll:
        o.append(f"- **{L[coll]}**: idle tick {delta('idle_tick_mean_ms', coll)}, mean tick under creature load {delta('entities_tick_mean_ms', coll)}, startup {delta('startup_fresh_s', coll)}, peak memory {delta('peak_working_set_mb', coll)}.")
        sp = S.get("sum_of_parts", {})
        if sp:
            k = "entities_tick_mean_ms" if "entities_tick_mean_ms" in sp else next(iter(sp))
            o.append(f"- **Together they cost {'about' if abs(sp[k]['measured_together'] - sp[k]['sum_of_singles']) < 0.15 * max(abs(sp[k]['sum_of_singles']), 1e-9) else 'more' if sp[k]['measured_together'] > sp[k]['sum_of_singles'] else 'less'} than the sum of their parts.** Adding up each mod's own creature-load tick cost gives {fmt(sp[k]['sum_of_singles'], 'ms')}; measured with all of them installed it was {fmt(sp[k]['measured_together'], 'ms')}. TODO interpret.")
    o.append("\nTODO closing line of the summary: who should install what.\n")
    o.append("## The mods we tested\n"); o.append(S["mods_table_md"] + "\n")
    o.append("TODO one or two sentences per mod on what it does and why server owners install it. Versions are the latest release for the game version at the time of the run, straight from the mod database. Default configuration throughout; no config files were edited.\n")
    o.append("## How we tested\n")
    o.append(f"The benchmark server is an ordinary game server on one of our nodes ({node}) running the official Vintage Story {game or ''} dedicated server. A small server-side mod drives the test, so no players or clients are involved:\n")
    o.append(f"1. **Startup**: timed from process launch to the moment the server reports it is running the game, on a fresh world with a fixed seed.\n2. **World generation**: the mod requests a square of chunk columns around spawn and waits until every column is loaded. Worldgen mods do their work here.\n3. **Idle**: nothing happens for a while; every tick is measured. This is what a mod costs when nobody is doing anything.\n4. **Creatures**: a fixed number of creatures are spawned, forced always-active, and ticks are measured again. This stands in for a busy server.\n5. The mod writes one JSON file and the server shuts down. A second run restarts on the same world to time reloading from disk.\n")
    o.append(f"Each mod set was run {runs_gen} times on a fresh world{' plus ' + str(runs_load) + ' reload runs' if runs_load else ''}, alternating the order so background noise on the node hits every set equally. Bars in the charts are the median of the runs; dots are the individual runs. The per-mod attribution numbers come from timing every game-tick listener and entity behaviour the mod registers; what a mod does through patches of game code is not separable and shows up only in the totals.\n")
    if a.scenario_b: o.append(f"## {a.scenario_a_label}\n"); o.append("TODO one line: this pass has no players connected; every spawned creature is forced active so the load is the same on every server.\n")
    o.append("## Startup\n"); o.append(f"![Server startup time]({a.images}/01_startup.png)\n")
    o.append(table([row("startup_fresh_s", "Fresh world"), row("startup_existing_s", "Existing world")]) + "\n")
    if (ch / "02_startup_phases.png").exists(): o.append(f"![Where startup time goes]({a.images}/02_startup_phases.png)\n")
    o.append("TODO interpret: which mods add asset loading time, whether it matters (startup happens once).\n")
    o.append("## World generation\n"); o.append(f"![Time to generate chunk columns around spawn]({a.images}/03_worldgen_time.png)\n")
    o.append(table([row("worldgen_wall_s", "Generate columns (wall-clock)"), row("worldgen_columns_per_s", "Throughput (columns/s)"), row("worldgen_cpu_s", "CPU time, all threads"), row("reload_wall_s", "Reload the same columns from disk")]) + "\n")
    o.append(f"![World generation wall-clock vs CPU time]({a.images}/04_worldgen_cpu.png)\n"); o.append("TODO interpret: worldgen mods (ruins, ore, trees) versus mods that do nothing here.\n")
    o.append("## Idle cost\n"); o.append(f"![Main-thread tick time at idle]({a.images}/05_tick_idle.png)\n")
    o.append(table([row("idle_tick_mean_ms", "Mean tick"), row("idle_tick_p99_ms", "99th percentile"), row("idle_cpu_pct_of_one_core", "Process CPU, % of one core")]) + "\n")
    if (ch / "15_systems_idle.png").exists(): o.append(f"![Where the idle tick time goes]({a.images}/15_systems_idle.png)\n")
    o.append("TODO interpret. The tick budget is 33.3 ms; put the deltas in that context.\n")
    if "entities_tick_mean_ms" in M:
        o.append("## Under creature load\n"); o.append(f"![Main-thread tick time with active creatures]({a.images}/06_tick_entities.png)\n")
        o.append(table([row("entities_tick_mean_ms", "Mean tick"), row("entities_tick_p50_ms", "Median"), row("entities_tick_p95_ms", "95th percentile"), row("entities_tick_p99_ms", "99th percentile"), row("entities_tick_max_ms", "Worst single tick"), row("entities_tps", "Ticks per second achieved")]) + "\n")
        o.append(f"![Distribution of tick durations under creature load]({a.images}/07_tick_cdf.png)\n")
        if (ch / "17_tick_timeline.png").exists(): o.append(f"![Tick time over the creature phase]({a.images}/17_tick_timeline.png)\n")
        if (ch / "16_systems_entities.png").exists(): o.append(f"![Where the tick time goes under creature load]({a.images}/16_systems_entities.png)\n")
        o.append("TODO interpret: which mods add per-entity cost (mods that add behaviours to all creatures are the usual suspects).\n")
    if (ch / "14_mod_attribution.png").exists():
        o.append("## What each mod's own code costs per tick\n"); o.append(f"![Tick time attributable to each mod's own code]({a.images}/14_mod_attribution.png)\n")
        o.append("TODO interpret. This chart only counts code the mod registers itself (tick listeners, block entities, entity behaviours). A mod whose cost is in patched game code or in extra content the game then has to process will look cheap here and expensive in the totals; say so where that happens.\n")
    o.append("## Memory\n"); o.append(f"![Memory use]({a.images}/08_memory.png)\n")
    o.append(table([row("peak_working_set_mb", "Peak working set"), row("heap_after_worldgen_mb", "Managed heap after world generation"), row("heap_after_entities_mb", "Managed heap after the creature phase"), row("peak_working_set_reload_mb", "Peak working set, reloading the saved world")]) + "\n")
    o.append("TODO interpret: assets vs live data; what plan size this implies.\n")
    o.append("## Garbage collection and CPU\n"); o.append(f"![Garbage-collector pause time]({a.images}/09_gc_pause.png)\n")
    o.append(table([row("worldgen_gc_pause_ms", "GC pause during world generation"), row("worldgen_gc_gen0", "Gen-0 collections during world generation"), row("worldgen_gc_gen2", "Gen-2 collections during world generation"), row("entities_gc_pause_ms", "GC pause during the creature phase")]) + "\n")
    o.append(f"![Total process CPU usage by phase]({a.images}/10_cpu_usage.png)\n"); o.append(f"![Achieved tick rate]({a.images}/11_tps.png)\n"); o.append("TODO interpret.\n")
    if (ch / "12_overhead_vs_baseline.png").exists():
        o.append("## All the costs on one page\n"); o.append(f"![What each mod set costs on top of the unmodded server]({a.images}/12_overhead_vs_baseline.png)\n")
    if (ch / "13_sum_of_parts.png").exists():
        o.append("## Do they add up?\n"); o.append(f"![Do the mods cost the sum of their parts?]({a.images}/13_sum_of_parts.png)\n")
        o.append("TODO interpret: if the measured collection costs more than the sum, the mods interfere (shared systems, extra content multiplying); if less, costs overlap (shared asset loading, one-off work).\n")
    if "ladder_table_md" in S:
        o.append("## Pushing it until it breaks\n"); o.append(f"![Tick time as the creature count climbs]({a.images}/18_ladder_tick.png)\n"); o.append(S["ladder_table_md"] + "\n"); o.append(f"![Tick rate as the creature count climbs]({a.images}/19_ladder_tps.png)\n"); o.append("TODO interpret.\n")
    if a.scenario_b:
        chb = pathlib.Path(a.scenario_b); SB = json.loads((chb / "summary.json").read_text()); MB = SB["metrics"]; ib = a.scenario_b_images
        o.append(f"## {a.scenario_b_label}\n")
        o.append("TODO explain the second scenario: a headless bot client joins each server and stands at spawn; creatures are spawned around it and left to the game's own activation rules, so distance-to-player logic in the game and in the mods is exercised. Everything else is identical to the first pass.\n")
        o.append(f"![What each mod set costs with a player online]({ib}/12_overhead_vs_baseline.png)\n")
        o.append("### Idle, player online\n"); o.append(f"![Main-thread tick time at idle, player online]({ib}/05_tick_idle.png)\n")
        o.append(table([row("idle_tick_mean_ms", "Mean tick", MB), row("idle_tick_p99_ms", "99th percentile", MB), row("idle_cpu_pct_of_one_core", "Process CPU, % of one core", MB)]) + "\n")
        if "entities_tick_mean_ms" in MB:
            o.append("### Under creature load, player online\n"); o.append(f"![Main-thread tick time with creatures around the player]({ib}/06_tick_entities.png)\n")
            o.append(table([row("entities_tick_mean_ms", "Mean tick", MB), row("entities_tick_p50_ms", "Median", MB), row("entities_tick_p95_ms", "95th percentile", MB), row("entities_tick_p99_ms", "99th percentile", MB), row("entities_tick_max_ms", "Worst single tick", MB), row("entities_tps", "Ticks per second achieved", MB)]) + "\n")
            o.append(f"![Distribution of tick durations, player online]({ib}/07_tick_cdf.png)\n")
            if (chb / "16_systems_entities.png").exists(): o.append(f"![Where the tick time goes under creature load, player online]({ib}/16_systems_entities.png)\n")
        o.append("### Startup, world generation, memory and GC, player online\n")
        o.append(table([row("startup_fresh_s", "Startup, fresh world", MB), row("worldgen_wall_s", "Generate columns (wall-clock)", MB), row("peak_working_set_mb", "Peak working set", MB), row("worldgen_gc_pause_ms", "GC pause during world generation", MB), row("entities_gc_pause_ms", "GC pause during the creature phase", MB)]) + "\n")
        if (chb / "13_sum_of_parts.png").exists(): o.append(f"![Do the mods cost the sum of their parts, player online?]({ib}/13_sum_of_parts.png)\n")
        o.append("TODO interpret the player scenario and contrast it with the empty-server numbers.\n")
    o.append("## Caveats\n")
    o.append("- No real players are connected, so nothing a mod does per player (packets, inventories, GUIs, commands) is measured.\n- The world is freshly generated with nothing built. Mods whose cost lives in placed blocks (machines, storage, farms) are undercounted; that cost is proportional to how many of those blocks your players build.\n- Creatures are forced active, which is harsher than a live server where most creatures idle.\n- Every mod ran with its default configuration. Config changes can move these numbers a lot.\n- One node, one plan size. Relative costs should transfer; absolute numbers will not.\n")
    o.append("## Reproduce it\n")
    o.append(f"The benchmark mod, the runner, the analysis script, the raw per-run JSON and the charts are in [the repository]({a.repo}). Point it at any server folder, list the mods you care about in `variants.json`, and run it.\n")
    o.append(f"*Benchmarked on {node}. Vintage Story {game or ''}.*\n")
    pathlib.Path(a.out).write_text("\n".join(o), encoding="utf-8")
    print("wrote", a.out, f"({len(o)} blocks, {sum(1 for x in o if 'TODO' in x)} TODO markers)")

if __name__ == "__main__":
    main()
