"""Aggregate mod-benchmark JSON results (one vanilla server build, N mod sets) into charts and a summary.

  python3 analyze_mods.py --results results/ny8-mods --out charts/ny8-mods --tag "(NY 8, 4 cores / 6 GB)" [--dark]
                          [--lock results/ny8-mods/variants.lock.json] [--baseline baseline] [--exclude foo-run1]

Every metric is reported per variant with its change against the baseline (vanilla, no mods). When a
collection variant exists, the "sum of parts" charts compare its measured cost with the sum of the single-mod costs.
Charts: 01 startup, 02 startup phases, 03 worldgen, 04 worldgen cpu, 05 idle tick, 06 creature tick, 07 tick CDF,
08 memory, 09 GC, 10 CPU, 11 TPS, 12 overhead vs baseline, 13 sum of parts, 14 per-mod attribution, 15/16 systems,
17 timeline, 18-20 ladder (if present). Plus summary.json, summary.md, mods.md.
"""
import argparse, json, pathlib, statistics as st, sys, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np

DARK = "--dark" in sys.argv
if DARK:
    SURFACE = "#182029"; TEXT = "#e6ebf0"; TEXT2 = "#a4afbb"; GRID = "#2a3440"; BASE_COLOR = "#8e99a6"
    SLOTS = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
    SEQ = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95"]
else:
    SURFACE = "#fcfcfb"; TEXT = "#0b0b0b"; TEXT2 = "#52514e"; GRID = "#e6e5e1"; BASE_COLOR = "#7a7974"
    SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
    SEQ = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95"]

rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": TEXT2,
    "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.titlecolor": TEXT, "axes.titleweight": "600",
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.titlelocation": "left", "axes.titlepad": 30, "legend.frameon": False,
    "text.color": TEXT, "legend.labelcolor": TEXT,
})

TAG = ""; LABELS = {}; COLORS = {}; ORDER = []; BASE = "baseline"; COLLECTION = None; LOCK = None; NO_DOTS = False


def load(results, exclude=()):
    runs = {}
    for f in sorted(results.glob("*-run*-*.json")):
        if any(f.name.startswith(x) for x in exclude): print("excluded", f.name); continue
        d = json.loads(f.read_text())
        if "error" in d: print("skipping", f.name, d["error"]); continue
        runs.setdefault((d["label"], d["mode"]), []).append(d)
    return runs


def med(xs): return float(st.median(xs)) if xs else float("nan")
def metric(runs, v, mode, phase, key): return [r[phase][key] for r in runs.get((v, mode), []) if phase in r]
def pct(base, new): return (new - base) / base * 100.0 if base else float("nan")


def subtitle(ax, text, width=118):
    ax.text(0, 1.02, "\n".join(textwrap.wrap(text + TAG, width)), transform=ax.transAxes, fontsize=9, color=TEXT2, va="bottom", linespacing=1.3)


def style_axes(ax):
    ax.set_axisbelow(True); ax.tick_params(length=0); ax.spines["bottom"].set_color(GRID)


def bars_with_runs(ax, groups, variants, data, unit, title, sub=None, fmt="{:.1f}", legend_loc="upper right"):
    n = len(variants); w = 0.8 / n; x = np.arange(len(groups)); ymax = 0
    for i, v in enumerate(variants):
        meds = [med(data[(v, g)]) for g in groups]
        xs = x - 0.4 + w * (i + 0.5)
        ax.bar(xs, meds, width=w - 0.03, color=COLORS[v], label=LABELS[v], linewidth=0, zorder=2)
        for xi, g, m in zip(xs, groups, meds):
            pts = data[(v, g)]
            if not NO_DOTS: ax.scatter([xi] * len(pts), pts, s=12, color=SURFACE, edgecolor=TEXT2, linewidth=0.8, zorder=3)
            if not np.isnan(m):
                top = m if NO_DOTS else max([m] + pts)
                ax.text(xi, top, fmt.format(m), ha="center", va="bottom", fontsize=8 if n > 4 else 9.5, color=TEXT, zorder=4, rotation=90 if n > 5 else 0)
                ymax = max(ymax, top)
    ax.set_xticks(x, groups); ax.set_ylabel(unit); ax.set_ylim(0, ymax * (1.3 if n > 5 else 1.18) if ymax else 1); ax.set_title(title)
    if sub: subtitle(ax, sub)
    ax.legend(loc=legend_loc, fontsize=8.5 if n > 4 else 9.5, ncol=1 if n <= 4 else 2); style_axes(ax)


def save(fig, out, name): fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(out / name); plt.close(fig); print("  wrote", name)


def main():
    global TAG, LABELS, COLORS, ORDER, BASE, COLLECTION, LOCK
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results"); ap.add_argument("--out", default="charts")
    ap.add_argument("--tag", default=""); ap.add_argument("--exclude", default=""); ap.add_argument("--dark", action="store_true")
    ap.add_argument("--lock", default=None, help="variants.lock.json (default: <results>/variants.lock.json)")
    ap.add_argument("--baseline", default="baseline")
    ap.add_argument("--only", default="", help="comma list of variant ids to chart (others are dropped from this run; keep a full run for the tables)")
    ap.add_argument("--no-dots", action="store_true", help="bars without the per-run dots")
    ap.add_argument("--relabel", default="", help="id=Label;id=Label overrides for chart legends")
    a = ap.parse_args()
    TAG = (" " + a.tag) if a.tag else ""; BASE = a.baseline
    res = pathlib.Path(a.results); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    runs = load(res, [x for x in a.exclude.split(",") if x])
    if a.only:
        keep = set(a.only.split(",")); runs = {k: v for k, v in runs.items() if k[0] in keep}
    global NO_DOTS; NO_DOTS = a.no_dots
    lock_path = pathlib.Path(a.lock) if a.lock else res / "variants.lock.json"
    LOCK = json.loads(lock_path.read_text()) if lock_path.exists() else None

    # ---- variant order, labels, colours ----
    present = {k[0] for k in runs}
    if LOCK:
        ORDER = [v["id"] for v in LOCK["variants"] if v["id"] in present]
        for v in LOCK["variants"]:
            lab = v["label"]
            if len(v["mods"]) == 1 and v["mods_resolved"]: lab = f"{v['mods_resolved'][0]['label']} {v['mods_resolved'][0]['version']}"
            LABELS[v["id"]] = lab
            if v.get("collection"): COLLECTION = v["id"]
    else:
        ORDER = ([BASE] if BASE in present else []) + sorted(x for x in present if x not in (BASE, "all")) + (["all"] if "all" in present else [])
        LABELS = {v: v for v in ORDER}
        if "all" in present: COLLECTION = "all"
    for v in present - set(ORDER): ORDER.append(v); LABELS.setdefault(v, v)
    if COLLECTION not in present: COLLECTION = None
    for kv in [x for x in a.relabel.split(";") if "=" in x]:   # id=Label;id=Label (labels may contain commas)
        k, lab = kv.split("=", 1); LABELS[k] = lab
    singles = [v for v in ORDER if v != BASE and v != COLLECTION]
    if len(singles) + (1 if COLLECTION else 0) > len(SLOTS): print(f"WARNING: {len(ORDER)} variants exceeds the {len(SLOTS)} categorical slots; split into several runs or facet")
    slot = 0
    for v in ORDER:
        if v == BASE: COLORS[v] = BASE_COLOR
        else: COLORS[v] = SLOTS[slot % len(SLOTS)]; slot += 1
    V = ORDER
    print("variants:", ", ".join(f"{v} ({LABELS[v]}, {len(runs.get((v, 'gen'), []))} gen / {len(runs.get((v, 'load'), []))} load runs)" for v in V))
    summary = {"baseline": BASE, "collection": COLLECTION, "game_version": next((r.get("game_version") for rs in runs.values() for r in rs if r.get("game_version")), None), "variants": [{"id": v, "label": LABELS[v], "color": COLORS[v]} for v in V],
               "runs": {f"{k[0]}/{k[1]}": len(x) for k, x in runs.items()}, "metrics": {}}

    def record(name, unit, per_variant, lower_is_better=True):
        m = {v: {"median": med(xs), "runs": xs} for v, xs in per_variant.items()}
        b = m.get(BASE, {}).get("median", float("nan"))
        m["change_pct"] = {v: pct(b, m[v]["median"]) for v in per_variant if v != BASE}
        m["delta"] = {v: m[v]["median"] - b for v in per_variant if v != BASE}
        m["unit"] = unit; m["lower_is_better"] = lower_is_better
        summary["metrics"][name] = m

    cols = next((r["worldgen"]["columns"] for rs in runs.values() for r in rs if "worldgen" in r), 0)
    chunks = next((r["worldgen"]["chunks"] for rs in runs.values() for r in rs if "worldgen" in r), 0)
    ents = next((r["entities"]["entities_spawned"] for rs in runs.values() for r in rs if "entities" in r), 0)
    nmods = len(singles)
    anyrun = next((r for rs in runs.values() for r in rs), {})
    players = anyrun.get("players_online_at_start", 0) or 0; forced = anyrun.get("creatures_always_active", True)
    scenario = (f"{players} player online at spawn; creatures spawned within {anyrun.get('spawn_range')} blocks and simulated by the game's own rules." if players
                else "No players online; creatures forced active.")

    # ---------- 01 startup ----------
    data = {}
    for v in V:
        data[(v, "Fresh world")] = [r["startup_ms"] / 1000 for r in runs.get((v, "gen"), [])]
        data[(v, "Existing world")] = [r["startup_ms"] / 1000 for r in runs.get((v, "load"), [])]
    record("startup_fresh_s", "s", {v: data[(v, "Fresh world")] for v in V}); record("startup_existing_s", "s", {v: data[(v, "Existing world")] for v in V})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, ["Fresh world", "Existing world"], V, data, "seconds (lower is better)", "Server startup time",
                   "From process launch until the server reports it is running the game. Mods add asset loading, JSON patching and their own init.")
    save(fig, out, "01_startup.png")

    # ---------- 02 startup phase breakdown (stacked, median per segment) ----------
    phase_rows = {}
    for v in V:
        segs = {}
        for r in runs.get((v, "gen"), []):
            rp = r.get("run_phases_ms")
            if not rp: continue
            items = sorted(rp.items(), key=lambda kv: kv[1]); prev = 0; prev_name = "process start"
            for name, t in items:
                segs.setdefault(f"{prev_name} → {name}", []).append((t - prev) / 1000); prev, prev_name = t, name
        if segs: phase_rows[v] = {k: med(x) for k, x in segs.items()}
    if phase_rows:
        keys = []
        for v in V:
            for k in phase_rows.get(v, {}): 
                if k not in keys: keys.append(k)
        fig, ax = plt.subplots(figsize=(9, 2.3 + 0.55 * len(V)), dpi=160)
        y = np.arange(len(V)); left = np.zeros(len(V))
        for i, k in enumerate(keys):
            vals = np.array([phase_rows.get(v, {}).get(k, 0) for v in V])
            ax.barh(y, vals, left=left, height=0.6, color=SEQ[min(i, len(SEQ) - 1)], label=k, linewidth=0, zorder=2, edgecolor=SURFACE)
            left += vals
        for yi, tot in zip(y, left): ax.text(tot, yi, f" {tot:.1f} s", va="center", fontsize=9, color=TEXT)
        ax.set_yticks(y, [LABELS[v] for v in V]); ax.invert_yaxis(); ax.set_xlabel("seconds since process start (median of runs)")
        ax.set_title("Where startup time goes"); subtitle(ax, "Server run phases as the benchmark mod sees them. The first segment is everything before the mod is loaded (runtime start, core asset load).", width=100)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), fontsize=8, ncol=3); ax.grid(True, axis="x", color=GRID); ax.grid(False, axis="y"); ax.set_axisbelow(True); ax.tick_params(length=0); ax.set_xlim(0, left.max() * 1.18)
        summary["startup_phases_s"] = phase_rows
        save(fig, out, "02_startup_phases.png")

    # ---------- 03/04 worldgen ----------
    data = {}
    for v in V:
        data[(v, "Generate new chunks")] = [x / 1000 for x in metric(runs, v, "gen", "worldgen", "wall_ms")]
        data[(v, "Reload from disk")] = [x / 1000 for x in metric(runs, v, "load", "worldgen", "wall_ms")]
    record("worldgen_wall_s", "s", {v: data[(v, "Generate new chunks")] for v in V}); record("reload_wall_s", "s", {v: data[(v, "Reload from disk")] for v in V})
    record("worldgen_columns_per_s", "columns/s", {v: [cols / x for x in data[(v, "Generate new chunks")]] for v in V}, lower_is_better=False)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, ["Generate new chunks", "Reload from disk"], V, data, "seconds (lower is better)",
                   f"Time to load {cols:,} chunk columns ({chunks:,} chunks) around spawn", ("Bars are the median of all runs" + ("" if NO_DOTS else "; dots are individual runs") + ". Fresh world, fixed seed. Worldgen mods do their work here."))
    save(fig, out, "03_worldgen_time.png")
    data = {}
    for v in V:
        data[(v, "Wall-clock time")] = [x / 1000 for x in metric(runs, v, "gen", "worldgen", "wall_ms")]
        data[(v, "CPU time (all threads)")] = [x / 1000 for x in metric(runs, v, "gen", "worldgen", "cpu_ms")]
    record("worldgen_cpu_s", "s", {v: data[(v, "CPU time (all threads)")] for v in V})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, ["Wall-clock time", "CPU time (all threads)"], V, data, "seconds", "World generation: wall-clock vs total CPU time", "CPU time higher than wall time means work ran in parallel across cores.")
    save(fig, out, "04_worldgen_cpu.png")

    # ---------- 05/06 tick time ----------
    for phase, fname, title, sub in [
        ("idle", "05_tick_idle.png", f"Main-thread tick time at idle ({cols:,} chunk columns loaded, " + (f"{players} player" if players else "no players") + ")", "Lower is better. Measured on every server tick for the whole phase. This is what a mod costs when nothing is happening."),
        ("entities", "06_tick_entities.png", f"Main-thread tick time with {ents} " + ("active " if forced else "") + "creatures", "Lower is better. Vintage Story budgets 33.3 ms per tick (30 TPS). " + scenario),
    ]:
        data = {}
        for v in V:
            for g, k in [("mean", "tick_mean_ms"), ("median", "tick_p50_ms"), ("p95", "tick_p95_ms"), ("p99", "tick_p99_ms")]:
                data[(v, g)] = metric(runs, v, "gen", phase, k)
        for g, k in [("mean", "tick_mean_ms"), ("median", "tick_p50_ms"), ("p95", "tick_p95_ms"), ("p99", "tick_p99_ms"), ("max", "tick_max_ms")]:
            record(f"{phase}_tick_{g}_ms", "ms", {v: metric(runs, v, "gen", phase, k) for v in V})
        if not any(data.values()): continue
        fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
        bars_with_runs(ax, ["mean", "median", "p95", "p99"], V, data, "milliseconds per tick", title, sub, fmt="{:.2f}", legend_loc="upper left")
        save(fig, out, fname)

    # ---------- 07 CDF ----------
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160); any_cdf = False
    for v in V:
        pooled = sorted(x for r in runs.get((v, "gen"), []) if "entities" in r for x in r["entities"]["ticks"])
        if not pooled: continue
        any_cdf = True; ys = np.arange(1, len(pooled) + 1) / len(pooled) * 100
        ax.plot(pooled, ys, color=COLORS[v], linewidth=2, label=LABELS[v])
    if any_cdf:
        ax.set_xscale("log"); ax.set_xlim(0.3, 300)
        ax.set_xticks([0.5, 1, 2, 5, 10, 20, 33.3, 50, 100, 200], ["0.5", "1", "2", "5", "10", "20", "33", "50", "100", "200"])
        ax.axvline(33.3, color=TEXT2, linewidth=0.8, linestyle=(0, (4, 3))); ax.text(34, 5, "33.3 ms budget", fontsize=9, color=TEXT2, rotation=90, va="bottom")
        ax.set_xlabel("tick duration, ms (log scale)"); ax.set_ylabel("% of ticks at or below")
        ax.set_title(f"How long ticks take with {ents} " + ("active " if forced else "") + "creatures: distribution")
        subtitle(ax, "Every tick from every run pooled. Further left is faster; a curve that reaches 100% sooner has a shorter tail.")
        ax.legend(loc="lower right", fontsize=9); style_axes(ax); ax.grid(True, axis="x", color=GRID, linewidth=0.5)
        save(fig, out, "07_tick_cdf.png")
    else: plt.close(fig)

    # ---------- 08 memory ----------
    data = {}
    for v in V:
        data[(v, "Peak working set")] = [r["peak_working_set_mb"] for r in runs.get((v, "gen"), [])]
        data[(v, "Heap after worldgen")] = metric(runs, v, "gen", "worldgen", "managed_heap_end_mb")
        data[(v, "Heap after creatures")] = metric(runs, v, "gen", "entities", "managed_heap_end_mb")
    record("peak_working_set_mb", "MB", {v: data[(v, "Peak working set")] for v in V}); record("heap_after_worldgen_mb", "MB", {v: data[(v, "Heap after worldgen")] for v in V})
    record("heap_after_entities_mb", "MB", {v: data[(v, "Heap after creatures")] for v in V})
    record("peak_working_set_reload_mb", "MB", {v: [r["peak_working_set_mb"] for r in runs.get((v, "load"), [])] for v in V})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, ["Peak working set", "Heap after worldgen", "Heap after creatures"], V, data, "MB", "Memory use",
                   "Working set is what the OS sees; managed heap is .NET's own allocation after the phase ended. Mod assets and extra block/entity data live here.", fmt="{:.0f}")
    save(fig, out, "08_memory.png")

    # ---------- 09 GC, 10 CPU, 11 TPS ----------
    phases = [("World generation", "worldgen"), ("Idle", "idle"), (f"{ents} creatures", "entities")]
    data = {}
    for v in V:
        for g, ph in phases:
            data[(v, g)] = metric(runs, v, "gen", ph, "gc_pause_ms")
            for k in ("cpu_ms", "gc_pause_ms", "gc_gen0", "gc_gen2"): record(f"{ph}_{k}", k.split("_")[-1] if "gc_gen" in k else "ms", {vv: metric(runs, vv, "gen", ph, k) for vv in V})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, [g for g, _ in phases], V, data, "ms paused for GC during phase", "Garbage-collector pause time", "Time all threads were stopped for .NET garbage collection. Lower is smoother.", fmt="{:.0f}")
    save(fig, out, "09_gc_pause.png")
    data = {}
    for v in V:
        for g, ph in phases[1:]:
            vals = [r[ph]["cpu_ms"] / r[ph]["wall_ms"] * 100 for r in runs.get((v, "gen"), []) if ph in r]
            data[(v, g)] = vals; record(f"{ph}_cpu_pct_of_one_core", "%", {vv: [r[ph]["cpu_ms"] / r[ph]["wall_ms"] * 100 for r in runs.get((vv, "gen"), []) if ph in r] for vv in V})
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, [g for g, _ in phases[1:]], V, data, "% of one CPU core (all threads)", "Total process CPU usage by phase", "100% = one core fully busy. Includes worker threads, not just the main thread.", fmt="{:.0f}%", legend_loc="upper left")
    save(fig, out, "10_cpu_usage.png")
    data = {}
    for v in V:
        for g, ph in phases[1:]:
            data[(v, g)] = [r[ph]["tick_count"] / (r[ph]["wall_ms"] / 1000) for r in runs.get((v, "gen"), []) if ph in r]
            record(f"{ph}_tps", "ticks/s", {vv: [r[ph]["tick_count"] / (r[ph]["wall_ms"] / 1000) for r in runs.get((vv, "gen"), []) if ph in r] for vv in V}, lower_is_better=False)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
    bars_with_runs(ax, [g for g, _ in phases[1:]], V, data, "ticks per second (target 30)", "Achieved tick rate", "The server targets 30 ticks per second; higher is better up to 30.", legend_loc="lower right")
    save(fig, out, "11_tps.png")

    # ---------- 12 overhead vs baseline (small multiples of deltas) ----------
    KEY = [("startup_fresh_s", "Startup, fresh world", "s", "{:+.1f} s"), ("worldgen_wall_s", f"Generate {cols:,} columns", "s", "{:+.1f} s"),
           ("idle_tick_mean_ms", "Idle mean tick", "ms", "{:+.2f} ms"), ("entities_tick_mean_ms", f"Mean tick, {ents} creatures", "ms", "{:+.2f} ms"),
           ("entities_tick_p99_ms", f"p99 tick, {ents} creatures", "ms", "{:+.1f} ms"), ("peak_working_set_mb", "Peak memory", "MB", "{:+.0f} MB")]
    KEY = [k for k in KEY if k[0] in summary["metrics"] and not np.isnan(summary["metrics"][k[0]].get(BASE, {}).get("median", float("nan")))]
    others = [v for v in V if v != BASE]
    if others and KEY:
        ncol = 3; nrow = int(np.ceil(len(KEY) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(11, 1.4 + nrow * (1.0 + 0.42 * len(others))), dpi=160, squeeze=False)
        for ax, (name, title, unit, fmt) in zip(axes.flat, KEY):
            m = summary["metrics"][name]; y = np.arange(len(others))
            vals = [m["delta"][v] for v in others]; pc = [m["change_pct"][v] for v in others]
            ax.barh(y, vals, height=0.62, color=[COLORS[v] for v in others], linewidth=0, zorder=2)
            lim = max(abs(x) for x in vals if not np.isnan(x)) or 1
            for yi, val, p in zip(y, vals, pc):
                if np.isnan(val): continue
                ax.text(max(val, 0) + lim * 0.04, yi, fmt.format(val) + f" ({p:+.0f}%)", va="center", ha="left", fontsize=8.5, color=TEXT)
            ax.axvline(0, color=TEXT2, linewidth=0.8); ax.set_xlim(-lim * 1.15 if min(vals) < 0 else -lim * 0.05, lim * 2.1)
            ax.set_yticks(y, [LABELS[v] for v in others] if ax in axes[:, 0] else [""] * len(others)); ax.invert_yaxis()
            ax.set_title(title, fontsize=10.5, pad=6); ax.grid(True, axis="x", color=GRID); ax.grid(False, axis="y"); ax.set_axisbelow(True); ax.tick_params(length=0, labelsize=8.5)
            ax.set_xlabel(f"change vs {LABELS.get(BASE, BASE)} ({unit})", fontsize=8.5)
        for ax in axes.flat[len(KEY):]: ax.axis("off")
        fig.suptitle("What each mod set costs on top of the unmodded server" + TAG, x=0.01, ha="left", fontsize=13, fontweight="600", color=TEXT)
        fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(out / "12_overhead_vs_baseline.png"); plt.close(fig); print("  wrote 12_overhead_vs_baseline.png")

    # ---------- 13 collection vs sum of parts ----------
    if COLLECTION and len(singles) >= 2 and KEY:
        rows = []
        for name, title, unit, fmt in KEY:
            m = summary["metrics"][name]
            s = sum(m["delta"][v] for v in singles if v in m["delta"] and not np.isnan(m["delta"][v]))
            t = m["delta"].get(COLLECTION, float("nan"))
            rows.append((title, unit, fmt, s, t)); summary.setdefault("sum_of_parts", {})[name] = {"sum_of_singles": s, "measured_together": t, "unit": unit}
        ncol = 3; nrow = int(np.ceil(len(rows) / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(11, 1.6 + 2.2 * nrow), dpi=160, squeeze=False)
        for ax, (title, unit, fmt, s, t) in zip(axes.flat, rows):
            ax.bar([0, 1], [s, t], width=0.6, color=[BASE_COLOR, COLORS[COLLECTION]], linewidth=0, zorder=2)
            top = max(abs(s), abs(t)) or 1
            for xi, val in zip([0, 1], [s, t]): ax.text(xi, val if val >= 0 else 0, fmt.format(val), ha="center", va="bottom", fontsize=9, color=TEXT)
            ax.axhline(0, color=TEXT2, linewidth=0.8); ax.set_ylim(min(0, min(s, t) * 1.3), top * 1.35)
            ax.set_xticks([0, 1], ["Sum of each\nmod alone", "All together,\nmeasured"]); ax.set_title(title, fontsize=10.5, pad=6); ax.set_ylabel(f"change vs baseline ({unit})", fontsize=8.5)
            style_axes(ax); ax.tick_params(labelsize=8.5)
        for ax in axes.flat[len(rows):]: ax.axis("off")
        fig.suptitle(f"Do {nmods} mods cost the sum of their parts?" + TAG, x=0.01, ha="left", fontsize=13, fontweight="600", color=TEXT)
        fig.text(0.01, 0.905, "Grey: the individual mods' costs added up. Coloured: the cost measured with all of them installed together. Taller coloured bar = mods interfere.", fontsize=9, color=TEXT2)
        fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(out / "13_sum_of_parts.png"); plt.close(fig); print("  wrote 13_sum_of_parts.png")

    # ---------- 14 per-mod attribution (listeners + behaviours declared by mods) ----------
    attrib = {}  # (variant, phase) -> {mod: ms per tick}
    for v in V:
        for ph in ("idle", "entities"):
            acc = {}
            for r in runs.get((v, "gen"), []):
                mm = r.get(ph, {}).get("mods_ms")
                if not mm: continue
                n = r[ph]["tick_count"] or 1
                for k, x in mm.items():
                    mod = k.split("/")[0]; acc.setdefault(mod, []).append(0)
                    acc[mod][-1] += x["total_ms"] / n
            if acc: attrib[(v, ph)] = {k: med(x) for k, x in acc.items()}
    mods_seen = sorted({m for d in attrib.values() for m in d if m not in ("game", "suhbench")})  # suhbench = the benchmark's own 250 ms sampler
    if mods_seen:
        summary["mod_attribution_ms_per_tick"] = {f"{v}/{ph}": d for (v, ph), d in attrib.items()}
        fig, axes = plt.subplots(1, 2, figsize=(11, 2.6 + 0.7 * len(mods_seen)), dpi=160, sharey=True)
        for ax, ph, ttl in zip(axes, ("idle", "entities"), ("Idle", f"{ents} creatures")):
            y = np.arange(len(mods_seen)); series = []
            # alone: value from the mod's own single variant; together: from the collection variant
            alone = [next((attrib.get((v, ph), {}).get(m, 0) for v in singles if m in (LOCK and next((x["mods"] for x in LOCK["variants"] if x["id"] == v), [v]) or [v])), 0) for m in mods_seen]
            own = [next((COLORS[v] for v in singles if m in (LOCK and next((x["mods"] for x in LOCK["variants"] if x["id"] == v), [v]) or [v])), BASE_COLOR) for m in mods_seen]
            series.append(("Alone (own variant)", alone, own))
            if COLLECTION and (COLLECTION, ph) in attrib: series.append((f"Together ({LABELS[COLLECTION]})", [attrib[(COLLECTION, ph)].get(m, 0) for m in mods_seen], [COLORS[COLLECTION]] * len(mods_seen)))
            h = 0.76 / len(series)
            for i, (lab, vals, col) in enumerate(series):
                ys = y - 0.38 + h * (i + 0.5)
                ax.barh(ys, vals, height=h - 0.03, color=col, label=lab, linewidth=0, zorder=2, alpha=1 if i == 0 else 0.9)
                for yi, val in zip(ys, vals): ax.text(val, yi, f" {val:.3f}", va="center", fontsize=8.5, color=TEXT)
            ax.set_yticks(y, [LABELS.get(m, m) if m in LABELS else (LOCK and LOCK["mods"].get(m, {}).get("label") or m) for m in mods_seen]); ax.invert_yaxis()
            ax.set_title(ttl, fontsize=11, pad=6); ax.set_xlabel("ms per tick on the main thread (median of runs)", fontsize=9)
            xmax = max([x for _, vals, _ in series for x in vals] + [0.001]); ax.set_xlim(0, xmax * 1.35)
            ax.grid(True, axis="x", color=GRID); ax.grid(False, axis="y"); ax.set_axisbelow(True); ax.tick_params(length=0, labelsize=9)
        if COLLECTION: axes[1].legend(loc="upper center", bbox_to_anchor=(0, -0.32), fontsize=8.5, ncol=2)
        else: axes[1].text(0.0, -0.3, "Bars use each mod's own colour; no collection variant in this run.", transform=axes[1].transAxes, fontsize=8.5, color=TEXT2)
        fig.suptitle("Tick time directly attributable to each mod's own code" + TAG, x=0.01, ha="left", fontsize=13, fontweight="600", color=TEXT)
        fig.text(0.01, 0.9 if len(mods_seen) > 2 else 0.86, "Game-tick listeners (incl. block entities) and entity behaviours declared by the mod. Work done through Harmony patches or JSON-only content is not captured here.", fontsize=9, color=TEXT2)
        fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig(out / "14_mod_attribution.png"); plt.close(fig); print("  wrote 14_mod_attribution.png")

    # ---------- 15/16 systems breakdown ----------
    for ph, fname in [("idle", "15_systems_idle.png"), ("entities", "16_systems_entities.png")]:
        per = {}
        for v in V:
            acc = {}
            for r in runs.get((v, "gen"), []):
                sm = r.get(ph, {}).get("systems_ms")
                if not sm: continue
                n = r[ph]["tick_count"] or 1
                for k, x in sm.items(): acc.setdefault(k, []).append(x["total_ms"] / n)
            per[v] = {k: med(xs) for k, xs in acc.items()}
        if not any(per.values()): continue
        keys = [k for k in sorted({k for d in per.values() for k in d}, key=lambda k: -max(per[v].get(k, 0) for v in V)) if max(per[v].get(k, 0) for v in V) >= 0.01][:6]
        names = [k.replace("ServerSystem", "").replace(".OnServerTick", "").replace("EventManager.TriggerGameTick", "Mod + block tick listeners").replace("ServerMain.ProcessMainThreadTasks", "Main-thread task queue") for k in keys]
        fig, ax = plt.subplots(figsize=(9, 2.2 + 0.75 * len(keys) * max(1, len(V) / 3)), dpi=160)
        n = len(V); h = 0.8 / n; y = np.arange(len(keys))
        for i, v in enumerate(V):
            vals = [per[v].get(k, 0) for k in keys]; ys = y - 0.4 + h * (i + 0.5)
            ax.barh(ys, vals, height=h - 0.03, color=COLORS[v], label=LABELS[v], linewidth=0, zorder=2)
            for yi, val in zip(ys, vals): ax.text(val, yi, f" {val:.2f}", va="center", fontsize=7.5 if n > 4 else 9, color=TEXT)
        ax.set_yticks(y, names); ax.invert_yaxis(); ax.set_xlabel("ms per tick on the main thread (median of runs)")
        ax.set_title("Where the tick time goes: " + ("idle" if ph == "idle" else f"{ents} active creatures"))
        subtitle(ax, "Measured around each server system's tick call. Systems not listed cost well under 0.01 ms.", width=88)
        ax.legend(loc="lower right", fontsize=8.5); ax.grid(True, axis="x", color=GRID); ax.grid(False, axis="y"); ax.set_axisbelow(True); ax.tick_params(length=0)
        xmax = max(per[v].get(k, 0) for v in V for k in keys); ax.set_xlim(0, xmax * 1.25 if xmax else 1)
        save(fig, out, fname)
        for v in V: summary.setdefault("systems_per_tick_ms", {})[f"{v}/{ph}"] = {k: per[v].get(k, 0) for k in keys}

    # ---------- 17 timeline, entity phase, run 1 ----------
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=160); drew = False; peaks = []; allraw = []
    for v in V:
        rs = runs.get((v, "gen"), [])
        if not rs: continue
        r = rs[0]; ser = [p for p in r["tick_series"] if p[2] == 4]
        if not ser: continue
        drew = True; t0 = ser[0][0]
        t = np.array([p[0] - t0 for p in ser]) / 1000; y = np.array([p[1] for p in ser]); allraw.extend(y.tolist())
        if len(V) <= 3: ax.plot(t, y, color=COLORS[v], linewidth=0.6, alpha=0.25)
        k = max(1, int(len(y) / (t[-1] if t[-1] else 1)))
        ax.plot(t, np.convolve(y, np.ones(k) / k, mode="same"), color=COLORS[v], linewidth=2, label=LABELS[v])
        peaks.append(y.max())
    if drew:
        top = float(min(60, max(8, np.percentile(allraw, 98) * 1.6)))   # fit the load actually measured; clip spikes
        if top >= 38: ax.axhline(33.3, color=TEXT2, linewidth=0.8, linestyle=(0, (4, 3))); ax.text(0.2, 34, "33.3 ms tick budget (30 TPS)", fontsize=9, color=TEXT2, va="bottom")
        ax.set_ylim(0, top); ax.set_xlabel("seconds since creatures were spawned"); ax.set_ylabel("ms per tick")
        ax.set_title(f"Tick time over the {ents}-creature phase (run 1)")
        subtitle(ax, ("Faint: every tick. " if len(V) <= 3 else "") + f"Bold: 1-second rolling average. Y axis clipped at {top:.0f} ms; the tick budget is 33.3 ms. Worst single tick, usually at the spawn: {min(peaks):.0f} to {max(peaks):.0f} ms.", width=130)
        ax.legend(loc="upper right", fontsize=8.5, ncol=2 if len(V) > 4 else 1); style_axes(ax)
        save(fig, out, "17_tick_timeline.png")
    else: plt.close(fig)

    # ---------- 18-20 ladder, if present ----------
    lad = {v: [r for r in runs.get((v, "gen"), []) if r.get("ladder")] for v in V}
    if any(lad.values()):
        targets = next(r["ladder_targets"] for rs in lad.values() for r in rs)
        def sv(v, i, f): return [f(r["ladder"][i]) for r in lad[v] if len(r["ladder"]) > i]
        steps = {v: max(len(r["ladder"]) for r in lad[v]) if lad[v] else 0 for v in V}
        tbl = ["| Creatures spawned | " + " | ".join(f"{LABELS[v]} mean / p99 tick, TPS" for v in V) + " |", "|---|" + "---|" * len(V)]
        for i, tgt in enumerate(targets):
            cells = []
            for v in V:
                if i >= steps[v]: cells.append("did not reach"); continue
                mean = med(sv(v, i, lambda s: s["tick_mean_ms"])); p99 = med(sv(v, i, lambda s: s["tick_p99_ms"])); tps = med(sv(v, i, lambda s: s["tick_count"] / (s["wall_ms"] / 1000)))
                cells.append(f"{mean:.1f} / {p99:.1f} ms, {tps:.1f}")
                summary["metrics"][f"ladder_{tgt}_{v}"] = {"mean_ms": mean, "p99_ms": p99, "tps": tps, "entities_end": med(sv(v, i, lambda s: s["entities_end"]))}
            tbl.append(f"| {tgt:,} | " + " | ".join(cells) + " |")
        summary["ladder_table_md"] = "\n".join(tbl)
        fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
        for v in V:
            xs = [med(sv(v, i, lambda s: s["entities_end"])) for i in range(steps[v])]
            mean = [med(sv(v, i, lambda s: s["tick_mean_ms"])) for i in range(steps[v])]; p99 = [med(sv(v, i, lambda s: s["tick_p99_ms"])) for i in range(steps[v])]
            ax.plot(xs, mean, color=COLORS[v], linewidth=2.2, marker="o", markersize=5, label=f"{LABELS[v]}: mean")
            ax.plot(xs, p99, color=COLORS[v], linewidth=1.4, linestyle=(0, (4, 2)), marker="o", markersize=4, markerfacecolor=SURFACE, label=f"{LABELS[v]}: p99")
        ax.axhline(33.3, color=TEXT2, linewidth=0.8, linestyle=(0, (4, 3))); ax.text(targets[0] * 0.5, 34.5, "33.3 ms tick budget (30 TPS)", fontsize=9, color=TEXT2, va="bottom")
        ax.set_xlabel("loaded entities (spawned creatures + wild animals)"); ax.set_ylabel("ms per tick (median of runs)"); ax.set_title("Tick time as the creature count climbs")
        subtitle(ax, "Each step spawns more always-active creatures, then measures the ticks. Solid: mean; dashed: 99th percentile."); ax.legend(loc="upper left", fontsize=8, ncol=2); style_axes(ax); ax.set_xlim(left=0)
        save(fig, out, "18_ladder_tick.png")
        fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
        for v in V:
            xs = [med(sv(v, i, lambda s: s["entities_end"])) for i in range(steps[v])]; tps = [med(sv(v, i, lambda s: s["tick_count"] / (s["wall_ms"] / 1000))) for i in range(steps[v])]
            ax.plot(xs, tps, color=COLORS[v], linewidth=2.2, marker="o", markersize=5, label=LABELS[v])
        ax.axhline(30, color=TEXT2, linewidth=0.8, linestyle=(0, (4, 3))); ax.set_ylim(0, 33); ax.set_xlim(left=0)
        ax.set_xlabel("loaded entities (spawned creatures + wild animals)"); ax.set_ylabel("ticks per second achieved"); ax.set_title("Tick rate as the creature count climbs")
        subtitle(ax, "The server targets 30 ticks per second. Once a tick takes longer than 33 ms, the rate falls and players feel it."); ax.legend(loc="lower left", fontsize=9); style_axes(ax)
        save(fig, out, "19_ladder_tps.png")

    # ---------- mod table ----------
    loaded = {}
    for (v, mode), rs in runs.items():
        for r in rs:
            for m in r.get("mods", []):
                if not m.get("builtin"): loaded[m["modid"]] = m
    mods_md = ["| Mod | Version tested | Author | Mod DB |", "|---|---|---|---|"]
    if LOCK:
        for slug, m in LOCK["mods"].items():
            mods_md.append(f"| {m.get('label') or m.get('name') or slug} | {m.get('version')} | {m.get('author') or ''} | [{slug}]({m.get('url', 'https://mods.vintagestory.at/' + slug)}) |")
    else:
        for mid, m in loaded.items(): mods_md.append(f"| {m.get('name')} | {m.get('version')} | {', '.join(m.get('authors') or [])} | {mid} |")
    summary["mods_loaded"] = loaded; summary["mods_table_md"] = "\n".join(mods_md)
    (out / "mods.md").write_text("\n".join(mods_md))

    # ---------- summary tables ----------
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    head = "| Metric | " + " | ".join(LABELS[v] + ("" if v == BASE else " (vs baseline)") for v in V) + " |"
    lines = [head, "|---|" + "---|" * len(V)]
    for name, m in summary["metrics"].items():
        if "unit" not in m or BASE not in m: continue
        b = m[BASE]["median"]
        if np.isnan(b): continue
        cells = []
        for v in V:
            x = m.get(v, {}).get("median", float("nan"))
            if np.isnan(x): cells.append("n/a"); continue
            if v == BASE: cells.append(f"{x:,.2f} {m['unit']}")
            else:
                ch = m["change_pct"][v]; better = (ch < 0) == m["lower_is_better"]
                cells.append(f"{x:,.2f} {m['unit']} ({ch:+.1f}%{'' if abs(ch) < 2 else (' better' if better else ' worse')})")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    (out / "summary.md").write_text("\n".join(lines) + "\n\n" + "\n".join(mods_md))
    print("\n".join(lines[:40])); print("\n".join(mods_md))


if __name__ == "__main__":
    main()
