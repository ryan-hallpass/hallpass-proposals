#!/usr/bin/env python3
"""
Build a Hallpass cold-outreach proposal page from a city brief.

    python3 _template/build.py _template/cities/<slug>.json            # build <slug>/index.html
    python3 _template/build.py _template/cities/<slug>.json --no-og    # skip the share image

Run from the site root (the folder that holds vercel.json). Then deploy with:  vercel deploy --prod

What it does
  1. Renders _template/template.html with the brief's fields  ->  <slug>/index.html
  2. Downloads any photo given as an http(s) URL into <slug>/assets/ (local paths are copied)
  3. Renders a 1200x630 share image  ->  <slug>/assets/og.jpg  (needs Playwright + Chromium; skipped if missing)
Shared, fixed assets (logo, client logos, Andy Lennon photo, favicon) live in /assets at the site root.
"""
import json, os, re, sys, shutil, urllib.request, html
from jinja2 import Environment, FileSystemLoader, ChainableUndefined, select_autoescape
from markupsafe import Markup, escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"

def em(s):      # *word* -> orange emphasis
    return Markup(re.sub(r"\*(.+?)\*", r"<em>\1</em>", str(escape(s or ""))))
def strong(s):  # *pillars* -> teal bold inside the plan quote
    return Markup(re.sub(r"\*(.+?)\*", r"<strong>\1</strong>", str(escape(s or ""))))
def fine(s):    # (parenthetical) -> small muted aside
    return Markup(re.sub(r"(\([^)]*\))\s*$", r'<span class="fine">\1</span>', str(escape(s or ""))))
def plain(s):
    return re.sub(r"\*", "", s or "")

def fetch_photo(photo, slug, name):
    """Return a site-absolute src for a photo dict {src|url, alt}."""
    src = photo.get("src") or photo.get("url") or ""
    if not src:
        raise SystemExit(f"Missing photo for {name}")
    if src.startswith("/"):
        return src
    ext = os.path.splitext(src.split("?")[0])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    out_dir = os.path.join(ROOT, slug, "assets")
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, name + ext)
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": UA, "Referer": src})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
    else:
        shutil.copyfile(os.path.join(ROOT, src), dest)
    return f"/{slug}/assets/{name}{ext}"

def make_og(d, slug):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ! Playwright not installed: skipped share image (og.jpg)"); return
    hero = os.path.join(ROOT, d["hero"]["photo"]["src"].lstrip("/"))
    logo = os.path.join(ROOT, "assets", "hallpass-logo.png")
    headline = str(em(d["hero"]["headline"]))
    page = f"""<html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&display=swap" rel="stylesheet"><style>
body{{margin:0;width:1200px;height:630px;font-family:Archivo,sans-serif;background:#f8efd9;background-image:linear-gradient(rgba(34,60,58,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(34,60,58,.06) 1px,transparent 1px);background-size:44px 44px;display:grid;grid-template-columns:1fr 470px;color:#223c3a;overflow:hidden}}
.l{{padding:56px 40px 50px 64px;display:flex;flex-direction:column;justify-content:space-between}}.logo{{width:150px}}
.e{{font-size:15px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;display:flex;gap:10px;align-items:center}}.e:before{{content:"";width:9px;height:9px;border-radius:50%;background:#e85427}}
h1{{font-size:58px;line-height:.98;letter-spacing:-.045em;margin:22px 0 0;font-weight:800}}h1 em{{font-style:normal;color:#e85427}}
.f{{font-size:18px;color:#56615d}}.r{{position:relative}}.r img{{width:100%;height:100%;object-fit:cover}}
.tag{{position:absolute;left:0;bottom:0;background:#f4bb35;padding:14px 20px;font-weight:700;font-size:13px;letter-spacing:.14em;text-transform:uppercase}}
</style></head><body><div class="l"><img class="logo" src="file://{logo}"><div><div class="e">Prepared for the {html.escape(d['city_full'])}</div><h1>{headline}</h1></div>
<div class="f">A place-marketing concept · proposals.hallpassdigital.com/{slug}</div></div>
<div class="r"><img src="file://{hero}"><div class="tag">{html.escape(d['hero']['photo_tag'])}</div></div></body></html>"""
    tmp = os.path.join(ROOT, slug, "assets", "_og.html")
    open(tmp, "w").write(page)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.goto("file://" + tmp, wait_until="networkidle"); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(ROOT, slug, "assets", "og.jpg"), type="jpeg", quality=85)
        b.close()
    os.remove(tmp)

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = json.load(open(sys.argv[1]))
    slug = d["slug"]
    d.setdefault("booking_url", "https://zcal.co/ryanmcneill/hallpass")
    print(f"Building /{slug}")
    d["hero"]["photo"]["src"] = fetch_photo(d["hero"]["photo"], slug, "hero")
    for i, c in enumerate(d["concepts"]["series"], 1):
        c["photo"]["src"] = fetch_photo(c["photo"], slug, f"concept-{i}")
    d["concepts"]["social"]["photo"]["src"] = fetch_photo(d["concepts"]["social"]["photo"], slug, "social")
    d["pov"]["photo"]["src"] = fetch_photo(d["pov"]["photo"], slug, "pov")
    env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["html"]), undefined=ChainableUndefined)
    env.filters.update(em=em, strong=strong, fine=fine, plain=plain)
    out = env.get_template("template.html").render(**d)
    os.makedirs(os.path.join(ROOT, slug), exist_ok=True)
    open(os.path.join(ROOT, slug, "index.html"), "w").write(out)
    print(f"  wrote {slug}/index.html")
    if "--no-og" not in sys.argv:
        make_og(d, slug); print(f"  wrote {slug}/assets/og.jpg")
    print(f"Done. Preview locally, then deploy:  vercel deploy --prod   ->  https://proposals.hallpassdigital.com/{slug}")

if __name__ == "__main__":
    main()
