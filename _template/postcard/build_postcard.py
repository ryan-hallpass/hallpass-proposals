#!/usr/bin/env python3
"""
Render a 6x11 Lob postcard (front + back) for a city brief.

    python3 _template/postcard/build_postcard.py _template/cities/<slug>.json

Writes, under _src/postcards/<slug>/:  postcard.pdf (2 pages, 11.25 x 6.25 in with bleed),
front.png and back.png proofs. The QR code points to the proposal with ?ref=postcard so
Vercel Web Analytics shows scans. Lob keeps the right side of the back clear for postage
and the address block (ink-free zone 4 x 2.375 in, 0.275 in from the right, 0.25 in from the bottom).
"""
import json, os, sys, base64, io, re, html
import qrcode
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))

def em(s): return Markup(re.sub(r"\*(.+?)\*", r"<em>\1</em>", str(escape(s or ""))))
def file_url(p): return "file://" + os.path.join(ROOT, p.lstrip("/"))

def main():
    d = json.load(open(sys.argv[1])); slug = d["slug"]
    url = f"https://proposals.hallpassdigital.com/{slug}?ref=postcard"
    img = qrcode.make(url, box_size=20, border=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    pc = d.get("postcard") or {}
    # Postcards are printed and mailed, so they need a photo licensed for commercial use
    # (CC BY / CC BY-SA / CC0 / public domain). Falls back to the web hero for proofs only.
    hero = pc.get("photo") or d["hero"]["photo"]["src"]
    if not hero.startswith("/") and not pc.get("photo"): hero = f"/{slug}/assets/hero.jpg"
    font = os.path.join(ROOT, "_template", "postcard", "archivo.woff2")
    env = Environment(loader=FileSystemLoader(HERE), autoescape=True); env.filters["em"] = em
    out = env.get_template("postcard.html").render(
        slug=slug, city_name=d["city_name"], city_full=d["city_full"], headline=d["hero"]["headline"],
        photo_tag=pc.get("photo_tag") or d["hero"]["photo_tag"], photo_pos=pc.get("photo_position", "center"), photo_credit=pc.get("photo_credit", ""), contact_first=(d.get("contact_name") or "").split(" ")[0],
        hero_url=file_url(hero), logo_url=file_url("/assets/hallpass-logo.png"),
        font_url="file://" + font, qr_data="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    od = os.path.join(ROOT, "_src", "postcards", slug); os.makedirs(od, exist_ok=True)
    src = os.path.join(od, "postcard.html"); open(src, "w").write(out)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 600}, device_scale_factor=3)
        pg.goto("file://" + src, wait_until="networkidle"); pg.wait_for_timeout(500)
        pg.pdf(path=os.path.join(od, "postcard.pdf"), width="11.25in", height="6.25in", print_background=True)
        sides = pg.query_selector_all(".side")
        sides[0].screenshot(path=os.path.join(od, "front.png")); sides[1].screenshot(path=os.path.join(od, "back.png"))
        b.close()
    print(f"Wrote _src/postcards/{slug}/postcard.pdf, front.png, back.png  (QR -> {url})")

if __name__ == "__main__":
    main()
