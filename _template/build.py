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


# Copy that changes by buyer type. A city JSON picks one with "variant" and can
# override any single string with a "copy" object.
VARIANTS = {
    "ed": {
        "concept": "place-marketing concept",
        "concept_title": "Place Marketing Concept",
        "plan_eyebrow": "Your plan says",
        "plan_lead": "The strategic direction is already set. The next step is a publishing system that gives that direction a recognizable voice, a steady cadence, and measurable reach.",
        "team": "economic development teams",
        "report_to": "reporting it internally",
        "step2_title": "Make {city} easier to evaluate",
        "step2_body": "Sector collateral, RFI-ready materials, and site-visit support answer the next questions.",
        "step3_body": "Turn qualified interest into direct economic-development conversations.",
        "signal_body": "A twelve-month program that turns {city}’s adopted strategy into steady publishing and board-ready reporting.",
        "cta": "Let’s put {city}’s story to work for its economic goals.",
        "cta_note": "Let’s spend 30 minutes on the plan, the near-term opportunity, and what a focused first phase could look like.",
        "footer": "Economic development & place marketing.",
        "report_row3": "Connection to the plan",
        "priorities": "the plan’s priorities",
    },
    "downtown": {
        "concept": "downtown-marketing concept",
        "concept_title": "Downtown Marketing Concept",
        "plan_eyebrow": "Your plan says",
        "plan_lead": "The direction is set. The next step is a publishing system that turns downtown’s businesses, events, and public spaces into stories people see every week.",
        "team": "downtown teams",
        "report_to": "reporting it to the board and partners",
        "step2_title": "Give people more reasons to come downtown",
        "step2_body": "Steady stories about owners, events, and new openings give people a reason to visit, stay longer, and come back.",
        "step3_body": "Turn attention into visits, openings, and leasing interest you can report to the board.",
        "signal_body": "A twelve-month program that turns downtown {city}’s plan into steady publishing and board-ready reporting.",
        "cta": "Let’s make downtown {city} impossible to miss.",
        "cta_note": "Let’s spend 30 minutes on the plan, the season ahead, and what a focused first phase could look like.",
        "footer": "Downtown & place marketing.",
        "report_row3": "Connection to the plan",
        "priorities": "the plan’s priorities",
    },
    "tourism": {
        "concept": "destination-marketing concept",
        "concept_title": "Destination Marketing Concept",
        "plan_eyebrow": "The opportunity",
        "plan_lead": "The investment is in place. The next step is a publishing system that turns it into visits, stays, and results your board and funders can see.",
        "team": "tourism teams",
        "report_to": "reporting it to the board and funders",
        "step2_title": "Make the trip easy to plan",
        "step2_body": "Itineraries, event pages, and partner offers answer the next question before a visitor asks it.",
        "step3_body": "Turn interest into booked stays, tournament bids, and meeting leads.",
        "signal_body": "A twelve-month program that turns {city}’s tourism investment into steady publishing and funder-ready reporting.",
        "cta": "Let’s fill {city}’s calendar.",
        "cta_note": "Let’s spend 30 minutes on your year-one goals, the events ahead, and what a focused first phase could look like.",
        "footer": "Destination & place marketing.",
        "report_row3": "Connection to your goals",
        "priorities": "your year-one priorities",
    },
}

# Client logo strip per variant ("Trusted by"). A city JSON can replace it with "logos".
LOGOS = {
    "downtown": [
        {"file": "ada.svg", "cls": "tall", "alt": "Ardmore Development Authority"},
        {"file": "royal-caribbean.svg", "cls": "", "alt": "Royal Caribbean"},
        {"file": "columbia.svg", "cls": "wide", "alt": "Columbia Records"},
        {"file": "ou.svg", "cls": "wide", "alt": "The University of Oklahoma"},
        {"file": "noble.png", "cls": "", "alt": "Noble Research Institute"},
        {"file": "bgca.svg", "cls": "", "alt": "Boys & Girls Clubs"},
    ],
    "ed": [
        {"file": "ada.svg", "cls": "tall", "alt": "Ardmore Development Authority"},
        {"file": "ou.svg", "cls": "wide", "alt": "The University of Oklahoma"},
        {"file": "noble.png", "cls": "", "alt": "Noble Research Institute"},
        {"file": "sea-cadets.png", "cls": "wide", "alt": "U.S. Naval Sea Cadet Corps"},
        {"file": "bgca.svg", "cls": "", "alt": "Boys & Girls Clubs"},
    ],
    "tourism": [
        {"file": "ada.svg", "cls": "tall", "alt": "Ardmore Development Authority"},
        {"file": "royal-caribbean.svg", "cls": "", "alt": "Royal Caribbean"},
        {"file": "columbia.svg", "cls": "wide", "alt": "Columbia Records"},
        {"file": "ou.svg", "cls": "wide", "alt": "The University of Oklahoma"},
        {"file": "noble.png", "cls": "", "alt": "Noble Research Institute"},
        {"file": "bgca.svg", "cls": "", "alt": "Boys & Girls Clubs"},
    ],
}

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
    if d["concepts"].get("social"):
        d["concepts"]["social"]["photo"]["src"] = fetch_photo(d["concepts"]["social"]["photo"], slug, "social")
    if d["concepts"].get("reel"):
        d["concepts"]["reel"]["photo"]["src"] = fetch_photo(d["concepts"]["reel"]["photo"], slug, "reel")
    d["pov"]["photo"]["src"] = fetch_photo(d["pov"]["photo"], slug, "pov")
    env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["html"]), undefined=ChainableUndefined)
    env.filters.update(em=em, strong=strong, fine=fine, plain=plain)
    copy = dict(VARIANTS[d.get("variant", "ed")]); copy.update(d.get("copy") or {})
    d["copy"] = {k: v.replace("{city}", d["city_name"]) for k, v in copy.items()}
    d.setdefault("prepared_for", "the " + d["city_full"])
    d.setdefault("logos", LOGOS[d.get("variant", "ed")])
    out = env.get_template("template.html").render(**d)
    os.makedirs(os.path.join(ROOT, slug), exist_ok=True)
    open(os.path.join(ROOT, slug, "index.html"), "w").write(out)
    print(f"  wrote {slug}/index.html")
    if "--no-og" not in sys.argv:
        make_og(d, slug); print(f"  wrote {slug}/assets/og.jpg")
    print(f"Done. Preview locally, then deploy:  vercel deploy --prod   ->  https://proposals.hallpassdigital.com/{slug}")

if __name__ == "__main__":
    main()
