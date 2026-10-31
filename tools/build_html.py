"""Turn the mod-benchmark blog Markdown + chart PNGs into one self-contained HTML page (images inlined).

  python build_html.py <post.md> <images dir> <out.html> [--design classic|plain] [--fragment]

--design classic : display heading font, eyebrow line, lede, KPI strip, boxed figures (the original page design)
--design plain   : single reading column, byline, KPI strip, unboxed figures (looks like an ordinary blog article)
Default output is a complete standalone document ready to drop on a web server.
--fragment writes only the <title>/<style>/content part for hosts that add their own document skeleton.
"""
import base64, datetime, pathlib, re, sys
import markdown

argv = sys.argv[1:]
design = argv[argv.index("--design") + 1] if "--design" in argv else "plain"
fragment = "--fragment" in argv
args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--design")]
md_path = pathlib.Path(args[0]); img_dir = pathlib.Path(args[1]); out = pathlib.Path(args[2])

raw = md_path.read_text(encoding="utf-8")
front, body = raw.split("---", 2)[1:3] if raw.startswith("---") else ("", raw)
meta = {k: v.strip().strip('"') for k, v in re.findall(r'^(\w+):[ \t]*(.*?)[ \t]*$', front, re.M)}
title = re.search(r"^# (.*)$", body, re.M).group(1).strip()
body = re.sub(r"^# .*\n", "", body.lstrip(), count=1)
words = len(re.findall(r"\w+", body)); minutes = max(1, round(words / 220))
html = markdown.markdown(body, extensions=["tables", "fenced_code", "sane_lists"])

def inline(alt, src):
    # a path that exists relative to the Markdown file wins (second-scenario images live in their own folder); else <images dir>/<basename>
    p = (md_path.parent / src) if (md_path.parent / src).exists() else img_dir / pathlib.Path(src).name
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{b64}" alt="{alt}" loading="lazy" width="1440" height="800"><figcaption>{alt}</figcaption></figure>'
html = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', lambda m: inline(m.group(1), m.group(2)), html)
html = html.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")

date = meta.get("date", ""); author = meta.get("author", "Something Unique Hosting"); desc = meta.get("description", "")
try: date_h = datetime.date.fromisoformat(date).strftime("%B %d, %Y").replace(" 0", " ")
except Exception: date_h = date

# KPI strip: front matter lines kpi1..kpi6 as "value | label | note | good|cost", e.g.
#   kpi1: "+0.3 ms | idle tick with all 6 mods | 1.45 -> 1.75 ms | cost"
KPIS = []
for i in range(1, 7):
    raw = meta.get(f"kpi{i}")
    if not raw: continue
    parts = [p.strip() for p in raw.split("|")] + ["", "", "good"]
    KPIS.append((parts[0], parts[1], parts[2], parts[3] if parts[3] in ("good", "cost") else "good"))
kpi_html = "".join(f'<div class="kpi kpi-{c}"><div class="kpi-value">{v}</div><div class="kpi-label">{l}</div><div class="kpi-note">{n}</div></div>' for v, l, n, c in KPIS)
REPO = meta.get("repo", "https://github.com/Something-Unique-Hosting/vintagestory-mod-benchmark")

meta_html = f"""<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{author}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>"""

if design == "classic":
    style = """<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow:wght@600;700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap">
<style>
/* Classic: one reading column (68ch) for prose; figures and tables break out to 920px; a four-tile KPI strip under the title. Dark only. */
:root {
  --bg: #10161d; --surface: #182029; --fg: #e6ebf0; --muted: #a4afbb; --rule: #2a3440; --accent: #86b6ef; --accent-soft: #1b2a3d;
  --good: #5dcf8a; --cost: #e8a15a; --code-bg: #1f2932; color-scheme: dark;
  --font-display: "Barlow", "Arial Narrow", Arial, sans-serif; --font-body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 17px; line-height: 1.55;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 0 64px; }
.wrap { max-width: 920px; margin: 0 auto; }
header { padding-block: 40px 8px; }
.eyebrow { font-family: var(--font-display); text-transform: uppercase; letter-spacing: .08em; font-size: 13px; color: var(--muted); font-weight: 600; }
.eyebrow a { color: inherit; text-decoration: none; }
h1 { font-family: var(--font-display); font-weight: 700; font-size: clamp(30px, 5vw, 46px); line-height: 1.08; margin: 10px 0 14px; text-wrap: balance; max-width: none; }
.lede { font-size: 20px; color: var(--muted); max-width: 70ch; margin: 0; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 28px 0 8px; }
.kpi { background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px 12px; min-width: 0; }
.kpi-value { font-family: var(--font-display); font-weight: 700; font-size: 38px; line-height: 1; color: var(--good); }
.kpi-cost .kpi-value { color: var(--cost); }
.kpi-label { font-weight: 600; margin-top: 6px; }
.kpi-note { color: var(--muted); font-size: 14px; margin-top: 2px; }
article { max-width: 80ch; }
article h2 { font-family: var(--font-display); font-weight: 700; font-size: 28px; line-height: 1.15; margin: 44px 0 10px; text-wrap: balance; padding-top: 18px; border-top: 1px solid var(--rule); }
article h3 { font-family: var(--font-display); font-weight: 600; font-size: 21px; margin: 28px 0 6px; }
article p { margin: 0 0 18px; }
article ul, article ol { padding-left: 1.3em; margin: 0 0 14px; }
article li { margin-bottom: 6px; }
article a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
article code { font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; font-size: .9em; background: var(--code-bg); padding: 1px 5px; border-radius: 3px; }
article pre { background: var(--code-bg); padding: 12px 14px; border-radius: 6px; overflow-x: auto; font-size: .9em; }
article strong { font-weight: 600; }
figure { margin: 18px 0 22px; width: min(920px, calc(100vw - 32px)); max-width: none; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 8px; }
figure img { display: block; width: 100%; height: auto; border-radius: 3px; }
figcaption { color: var(--muted); font-size: 13px; padding: 8px 6px 2px; }
.tablewrap { overflow-x: auto; margin: 10px 0 20px; width: min(920px, calc(100vw - 32px)); }
table { border-collapse: collapse; font-size: 15.5px; font-variant-numeric: tabular-nums; min-width: 100%; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-family: var(--font-display); font-weight: 600; letter-spacing: .02em; color: var(--muted); font-size: 14px; text-transform: uppercase; }
td:not(:first-child), th:not(:first-child) { text-align: right; white-space: nowrap; }
article > p:last-child em { color: var(--muted); }
footer { max-width: 920px; margin: 40px auto 0; padding-top: 18px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 14px; }
footer a { color: var(--accent); }
@media (max-width: 600px) { body { font-size: 16px; } .kpi-value { font-size: 32px; } }
</style>"""
    content = f"""<div class="wrap">
<header>
  <div class="eyebrow"><a href="https://suhosting.net/">Something Unique Hosting</a> · Vintage Story · {date_h}</div>
  <h1>{title}</h1>
  <p class="lede">{desc}</p>
  {("<div class=\"kpis\">" + kpi_html + "</div>") if KPIS else ""}
</header>
<article>
{html}
</article>
<footer>Benchmark code and raw data: <a href="{REPO}">{REPO.replace("https://", "")}</a></footer>
</div>"""
else:
    style = """<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap">
<style>
/* Plain: a single 760px reading column, byline, a four-number strip, unboxed full-width figures. Dark only. */
:root {
  --bg: #0f1419; --fg: #e4e8ec; --muted: #9aa5b1; --rule: #273039; --accent: #8ab8f0; --code-bg: #1a2129; --surface: #182029;
  --good: #5dcf8a; --cost: #e8a15a; color-scheme: dark;
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: "Inter", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 17px; line-height: 1.65;
  -webkit-font-smoothing: antialiased; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.site { max-width: 760px; margin: 0 auto; padding: 22px 0 14px; display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--rule); font-size: 14px; color: var(--muted); }
.site a { color: var(--fg); text-decoration: none; font-weight: 600; letter-spacing: .01em; }
.site a:hover { color: var(--accent); }
article { max-width: 760px; margin: 0 auto; padding: 36px 0 60px; }
article h1 { font-size: 2.1rem; line-height: 1.2; font-weight: 700; margin: 0 0 12px; letter-spacing: -.01em; }
.byline { color: var(--muted); font-size: 14.5px; margin: 0 0 24px; }
.byline span + span::before { content: " · "; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0; margin: 0 0 34px; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
.kpi { padding: 16px 14px 14px; min-width: 0; border-left: 1px solid var(--rule); }
.kpi:first-child { border-left: 0; padding-left: 0; }
.kpi-value { font-weight: 700; font-size: 30px; line-height: 1; letter-spacing: -.02em; color: var(--good); }
.kpi-cost .kpi-value { color: var(--cost); }
.kpi-label { font-weight: 600; font-size: 14px; margin-top: 7px; }
.kpi-note { color: var(--muted); font-size: 13px; margin-top: 2px; line-height: 1.4; }
article h2 { font-size: 1.45rem; line-height: 1.3; margin: 44px 0 12px; font-weight: 700; }
article h3 { font-size: 1.12rem; margin: 30px 0 8px; font-weight: 600; }
article p { margin: 0 0 16px; }
article ul, article ol { padding-left: 1.4em; margin: 0 0 16px; }
article li { margin-bottom: 7px; }
article a { color: var(--accent); text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 2px; }
article code { font-family: ui-monospace, "Cascadia Mono", Consolas, "Liberation Mono", monospace; font-size: .88em; background: var(--code-bg); padding: 1px 5px; border-radius: 4px; }
article pre { background: var(--code-bg); padding: 12px 14px; border-radius: 6px; overflow-x: auto; font-size: .88em; }
article strong { font-weight: 600; }
article em { color: var(--muted); }
figure { margin: 22px 0 26px; }
figure img { display: block; width: 100%; height: auto; border-radius: 4px; }
figcaption { color: var(--muted); font-size: 13.5px; margin-top: 8px; font-style: italic; }
.tablewrap { overflow-x: auto; margin: 10px 0 22px; }
table { border-collapse: collapse; width: 100%; font-size: 15px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-weight: 600; color: var(--muted); font-size: 13.5px; }
td:not(:first-child), th:not(:first-child) { text-align: right; white-space: nowrap; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 32px 0; }
footer { max-width: 760px; margin: 0 auto; padding: 18px 0 40px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 14px; }
footer a { color: var(--accent); }
@media (max-width: 600px) { body { font-size: 16px; } article h1 { font-size: 1.7rem; } .kpis { grid-template-columns: 1fr 1fr; } .kpi { border-left: 0; padding-left: 0; } }
</style>"""
    content = f"""<div class="site"><a href="https://suhosting.net/">Something Unique Hosting</a><span>Blog</span></div>
<article>
<h1>{title}</h1>
<p class="byline"><span>{author}</span><span>{date_h}</span><span>{minutes} min read</span></p>
{("<div class=\"kpis\">" + kpi_html + "</div>") if KPIS else ""}
{html}
</article>
<footer>Benchmark code and raw data: <a href="{REPO}">{REPO.replace("https://", "")}</a></footer>"""

head = meta_html + "\n" + style
if fragment:
    page = head + "\n" + content + "\n"
else:
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head}
</head>
<body>
{content}
</body>
</html>
"""
out.write_text(page, encoding="utf-8")
print("wrote", out, f"{out.stat().st_size/1024:.0f} KB", design, "(fragment)" if fragment else "(standalone)")
