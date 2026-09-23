#!/usr/bin/env python3
"""
Send a prospect's postcard through Lob.

    python3 _template/postcard/send_postcard.py davis            # TEST mode: free, not printed, gives a proof
    python3 _template/postcard/send_postcard.py davis --live     # LIVE: prints and mails (asks you to type the city name)

Reads API keys from .env in the site root (never committed):
    LOB_TEST_KEY=test_...
    LOB_LIVE_KEY=live_...
Recipient comes from "postcard.to" in _template/cities/<slug>.json.
Run build_postcard.py first so _src/postcards/<slug>/front.pdf and back.pdf exist.
"""
import json, os, sys, base64, urllib.request, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FROM = {"name": "Ryan McNeill", "company": "Hallpass", "address_line1": "201 W Main St",
        "address_city": "Ardmore", "address_state": "OK", "address_zip": "73401"}

def env():
    e = {}
    for line in open(os.path.join(ROOT, ".env")):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1); e[k.strip()] = v.strip().strip('"')
    return e

def multipart(fields, files):
    b = uuid.uuid4().hex; out = []
    for k, v in fields.items():
        out += [f"--{b}", f'Content-Disposition: form-data; name="{k}"', "", str(v)]
    body = "\r\n".join(out).encode() + b"\r\n"
    for k, path in files.items():
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{os.path.basename(path)}\"\r\n"
                 "Content-Type: application/pdf\r\n\r\n").encode() + open(path, "rb").read() + b"\r\n"
    return body + f"--{b}--\r\n".encode(), b

def main():
    slug = sys.argv[1]; live = "--live" in sys.argv
    d = json.load(open(os.path.join(ROOT, "_template", "cities", f"{slug}.json")))
    to = (d.get("postcard") or {}).get("to") or sys.exit("No postcard.to address in the city JSON.")
    key = env().get("LOB_LIVE_KEY" if live else "LOB_TEST_KEY") or sys.exit("Key missing from .env")
    if live:
        print(f"LIVE send to {to['name']}, {to.get('company','')}, {to['address_line1']}, {to['address_city']} {to['address_state']}")
        if input(f"Type '{slug}' to print and mail it: ").strip() != slug: sys.exit("Cancelled.")
    od = os.path.join(ROOT, "_src", "postcards", slug)
    fields = {"description": f"Hallpass proposal postcard - {d['city_full']}", "size": "6x11",
              "use_type": "marketing", "metadata[slug]": slug}
    for k, v in to.items(): fields[f"to[{k}]"] = v
    for k, v in FROM.items(): fields[f"from[{k}]"] = v
    body, boundary = multipart(fields, {"front": os.path.join(od, "front.pdf"), "back": os.path.join(od, "back.pdf")})
    req = urllib.request.Request("https://api.lob.com/v1/postcards", data=body, method="POST", headers={
        "Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode(),
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Idempotency-Key": f"{slug}-{'live' if live else 'test'}-{uuid.uuid4().hex[:8]}"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        sys.exit(f"Lob error {e.code}: {e.read().decode()}")
    rec = {k: r.get(k) for k in ("id", "url", "expected_delivery_date", "send_date", "carrier")}
    rec["mode"] = "live" if live else "test"
    json.dump(rec, open(os.path.join(od, f"lob-{rec['mode']}.json"), "w"), indent=2)
    print(json.dumps(rec, indent=2))

if __name__ == "__main__":
    main()
