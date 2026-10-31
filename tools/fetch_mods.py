#!/usr/bin/env python3
"""Resolve and download the mods named in a variants manifest from mods.vintagestory.at, then write the
runner inputs: mods/pool/*.zip, mods/sets/<variant>.list, mods/variants.lock.json, mods/variants.txt.

  python3 tools/fetch_mods.py harness/variants.json [--mods-dir mods] [--game 1.22.7]

Release choice: the newest release whose tags include the game version (exact match first, then same
major.minor), unless 'version' pins one. Already-downloaded files are kept.
"""
import argparse, json, pathlib, re, sys, urllib.request, urllib.parse

UA = "curl/8.5.0"
API = "https://mods.vintagestory.at/api/mod/"

def get(url, binary=False):
    rq = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(rq, timeout=120) as r:
        return r.read() if binary else json.loads(r.read().decode())

def vkey(v):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.\-+]", v)]

def pick_release(mod, game, pin):
    rels = mod["releases"]
    if pin:
        r = next((r for r in rels if r["modversion"] == pin), None)
        if not r: sys.exit(f"{mod['urlalias']}: version {pin} not found; have {[r['modversion'] for r in rels[:8]]}")
        return r
    exact = [r for r in rels if game in (r.get("tags") or [])]
    if exact: return max(exact, key=lambda r: vkey(r["modversion"]))
    mm = ".".join(game.split(".")[:2])
    close = [r for r in rels if any(t.startswith(mm + ".") or t == mm for t in (r.get("tags") or []))]
    if close:
        r = max(close, key=lambda r: vkey(r["modversion"]))
        print(f"  note: {mod['urlalias']} has no release tagged {game}; using {r['modversion']} tagged {r['tags'][-1]}")
        return r
    sys.exit(f"{mod['urlalias']}: no release for game {game} (tags seen: {sorted({t for r in rels for t in r.get('tags') or []})[-6:]})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest"); ap.add_argument("--mods-dir", default="mods"); ap.add_argument("--game", default=None)
    a = ap.parse_args()
    man = json.loads(pathlib.Path(a.manifest).read_text())
    game = a.game or man.get("game") or sys.exit("game version missing")
    mods_dir = pathlib.Path(a.mods_dir); pool = mods_dir / "pool"; sets = mods_dir / "sets"
    pool.mkdir(parents=True, exist_ok=True); sets.mkdir(parents=True, exist_ok=True)

    lock = {"game": game, "mods": {}, "variants": []}
    for slug, spec in man["mods"].items():
        spec = spec or {}
        if spec.get("file"):
            p = pathlib.Path(spec["file"]); dst = pool / p.name
            if not dst.exists(): dst.write_bytes(p.read_bytes())
            lock["mods"][slug] = {"slug": slug, "label": spec.get("label", slug), "version": spec.get("version", "local"), "file": p.name,
                                  "deps": spec.get("deps", []), "library": spec.get("library", False), "source": "local"}
            print(f"{slug:24s} local {p.name}"); continue
        d = get(API + urllib.parse.quote(slug))
        if d.get("statuscode") not in ("200", 200) or "mod" not in d: sys.exit(f"{slug}: API returned {str(d)[:200]}")
        m = d["mod"]; r = pick_release(m, game, spec.get("version"))
        fname = r["filename"]; dst = pool / fname
        if not dst.exists():
            data = get(r["mainfile"], binary=True); dst.write_bytes(data)
        lock["mods"][slug] = {"slug": slug, "label": spec.get("label") or m["name"], "name": m["name"], "author": m.get("author"),
                              "version": r["modversion"], "modidstr": r.get("modidstr"), "file": fname, "release_date": r.get("created"),
                              "game_tags": r.get("tags"), "download_url": r["mainfile"], "url": "https://mods.vintagestory.at/" + slug, "downloads_total": m.get("downloads"),
                              "deps": spec.get("deps", []), "library": spec.get("library", False), "source": "moddb"}
        print(f"{slug:24s} {m['name']!r:34s} v{r['modversion']:14s} {fname}  ({dst.stat().st_size // 1024} KB)")

    def files_for(slugs):
        out = []
        for s in slugs:
            for dep in lock["mods"][s]["deps"]:
                if lock["mods"][dep]["file"] not in out: out.append(lock["mods"][dep]["file"])
            if lock["mods"][s]["file"] not in out: out.append(lock["mods"][s]["file"])
        return out

    variants = man.get("variants")
    if not variants:
        under_test = [s for s, m in lock["mods"].items() if not m["library"]]
        variants = [{"id": "baseline", "label": f"Vanilla {game}, no mods", "mods": []}]
        variants += [{"id": s, "label": lock["mods"][s]["label"], "mods": [s]} for s in under_test]
        if len(under_test) > 1:
            variants.append({"id": "all", "label": f"All {len(under_test)} mods together", "mods": under_test, "collection": True})
    for v in variants:
        if not re.fullmatch(r"[a-z0-9_]+", v["id"]): sys.exit(f"variant id {v['id']!r}: use lowercase letters, digits, underscore only (file names depend on it)")
        v = dict(v); v["files"] = files_for(v["mods"]); v.setdefault("collection", len(v["mods"]) > 1)
        # optional per-variant mod config: {"Synergy.json": {...}} -> mods/sets/<id>.config/Synergy.json, copied into the run's ModConfig/
        cfgdir = sets / f"{v['id']}.config"
        if v.get("config"):
            cfgdir.mkdir(exist_ok=True)
            for fname, body in v["config"].items(): (cfgdir / fname).write_text(json.dumps(body, indent=2) if not isinstance(body, str) else body)
        elif cfgdir.exists():
            for x in cfgdir.iterdir(): x.unlink()
            cfgdir.rmdir()
        v["mods_resolved"] = [{"slug": s, "version": lock["mods"][s]["version"], "label": lock["mods"][s]["label"]} for s in v["mods"]]
        (sets / f"{v['id']}.list").write_text("\n".join(v["files"]) + ("\n" if v["files"] else ""))
        lock["variants"].append(v)
    (mods_dir / "variants.lock.json").write_text(json.dumps(lock, indent=2))
    (mods_dir / "variants.txt").write_text(",".join(v["id"] for v in lock["variants"]) + "\n")
    print("\nvariants:", ", ".join(f"{v['id']}[{len(v['files'])} files]" for v in lock["variants"]))
    print("VARIANTS=" + ",".join(v["id"] for v in lock["variants"]))
    print("wrote", mods_dir / "variants.lock.json")

if __name__ == "__main__":
    main()
