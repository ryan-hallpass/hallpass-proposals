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

PC_COPY = {
    "ed": {"note_lead": "We read {city}’s economic development plan and",
           "note_tail": "and how it can help the city reach its economic goals.",
           "read_line": "A two-minute read, built around your strategic plan"},
    "tourism": {"note_lead": "We saw the news about {city}’s tourism funding and",
                "note_tail": "and how it can turn that investment into visits, stays, and results your funders can see.",
                "read_line": "A two-minute read, built around your year-one goals"},
}

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
    pc_copy = dict(PC_COPY[d.get("variant", "ed")]); pc_copy.update(pc.get("copy") or {})
    pc_copy = {k: v.replace("{city}", d["city_name"]) for k, v in pc_copy.items()}
    pc_copy["note_lead_lc"] = pc_copy["note_lead"][:1].lower() + pc_copy["note_lead"][1:]
    out = env.get_template("postcard.html").render(
        slug=slug, city_name=d["city_name"], city_full=d["city_full"], headline=d["hero"]["headline"],
        prepared_for=d.get("prepared_for") or "the " + d["city_full"], pc_copy=pc_copy,
        photo_tag=pc.get("photo_tag") or d["hero"]["photo_tag"], photo_pos=pc.get("photo_position", "center"), photo_credit=pc.get("photo_credit", ""), contact_first=(d.get("contact_name") or "").split(" ")[0],
        hero_url=file_url(hero), logo_url=file_url("/assets/hallpass-logo.png"),
        font_url="file://" + font, qr_data="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    od = os.path.join(ROOT, "_src", "postcards", slug); os.makedirs(od, exist_ok=True)
    src = os.path.join(od, "postcard.html"); open(src, "w").write(out)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 600}, device_scale_factor=3)
        pg.goto("file://" + src, wait_until="networkidle"); pg.wait_for_timeout(500)
        pdf = dict(width="11.25in", height="6.25in", print_background=True)
        pg.pdf(path=os.path.join(od, "postcard.pdf"), **pdf)
        pg.pdf(path=os.path.join(od, "front.pdf"), page_ranges="1", **pdf)   # Lob takes front and back separately
        pg.pdf(path=os.path.join(od, "back.pdf"), page_ranges="2", **pdf)
        sides = pg.query_selector_all(".side")
        sides[0].screenshot(path=os.path.join(od, "front.png")); sides[1].screenshot(path=os.path.join(od, "back.png"))
        b.close()
    print(f"Wrote _src/postcards/{slug}/postcard.pdf, front.png, back.png  (QR -> {url})")

if __name__ == "__main__":
    main()
