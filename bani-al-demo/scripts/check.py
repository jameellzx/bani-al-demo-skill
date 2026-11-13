"""Check a built demo before the user sees it. All must pass.

    python check.py <slug>

1. Leftovers: none of the template's own text, image names or colours (slots.json "leftovers") in the page,
   and no text node that also appears in the template's own HTML copy (catches text hard-coded in sections).
   Allowed on purpose: fill.json "allow_text" / "allow_colors".
2. Facts: every fact slot (price, rating, review, press name …) still shown on the page has a source in
   fill.json "sources".
3. Phone: Playwright at 390x844 and 1440x900: every image loads, no sideways scroll, dir=rtl when Arabic,
   noindex meta, every link goes to wa.me. Screenshots: <client>/shots/phone.jpg, desktop.jpg (full page),
   phone_top.jpg (first screen).
Writes <client>/check.json. Exit 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser

from paths import client_dir, settings


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        t = " ".join(data.split())
        if t and not self.skip:
            self.out.append(t)


def texts(page):
    p = Text()
    p.feed(page)
    return p.out


def norm(t):
    return " ".join(re.sub(r"<[^>]+>", " ", t).split()).lower()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    slug = sys.argv[1]
    s = settings()
    cdir = client_dir(slug)
    fill = json.loads((cdir / "fill.json").read_text(encoding="utf-8-sig"))
    tdir = os.path.join(s["templates_dir"], fill["template"])
    slots = json.loads(open(os.path.join(tdir, "slots.json"), encoding="utf-8").read())
    page_path = cdir / "site" / "index.html"
    page = page_path.read_text(encoding="utf-8")
    body = page.split("<body", 1)[-1]
    page_text = " ".join(texts(page)).lower()
    allow_text = {norm(t) for t in fill.get("allow_text") or []}
    allow_colors = {c.upper() for c in fill.get("allow_colors") or []}
    fails, notes = [], []

    # 1. Leftovers.
    lo = slots["leftovers"]
    for t in lo["texts"]:
        n = norm(t)
        if n and n not in allow_text and n in page_text:
            fails.append(f"leftover text: {t[:80]}")
    for img in lo["images"]:
        if img in body:
            fails.append(f"leftover image: {img}")
    css = page.lower()
    for c in lo["colors"]:
        if c.upper() not in allow_colors and c.lower() in css:
            fails.append(f"leftover colour: {c} (add to color_map, or allow_colors if the client really uses it)")
    tpl_html = os.path.join(tdir, "html", "index.html")
    if os.path.exists(tpl_html):
        tpl = {norm(t) for t in texts(open(tpl_html, encoding="utf-8").read())}
        for t in dict.fromkeys(texts(page)):
            n = norm(t)
            if n in tpl and n not in allow_text and len(n) > 2 and not re.fullmatch(r"[\d\s.,:%/+\-–|·★☆]+", n):
                fails.append(f"template text still on page: {t[:80]}")

    # 2. Facts.
    index = json.loads((cdir / "build" / "templates" / "index.json").read_text(encoding="utf-8"))
    footer_p = cdir / "build" / "templates" / "footer-section.json"
    docs = {"index": index}
    if footer_p.exists():
        docs["footer-section"] = json.loads(footer_p.read_text(encoding="utf-8"))
    fact_keys = {(sl["section_type"], sl["block_type"], sl["setting_id"]) for sl in slots["slots"] if sl["fact"]}
    defaults = {(sl["section_type"], sl["block_type"], sl["setting_id"]): sl["value"] for sl in slots["slots"]}
    sources = fill.get("sources") or {}
    for file, doc in docs.items():
        secs = doc.get("sections", doc)
        for key in doc.get("order", list(secs)):
            sec = secs[key]
            if sec.get("disabled"):
                continue
            pairs = [(None, None, sec.get("settings") or {})]
            for bkey in sec.get("block_order", list((sec.get("blocks") or {}).keys())):
                b = sec["blocks"][bkey]
                if not b.get("disabled"):
                    pairs.append((bkey, b["type"], b.get("settings") or {}))
            for bkey, btype, st in pairs:
                for (stype, bt, sid) in fact_keys:
                    if stype != sec["type"] or bt != btype:
                        continue
                    val = st.get(sid, defaults.get((stype, bt, sid)))
                    if val in (None, "", 0, "0", "<p></p>"):
                        continue
                    path = f"{file}:{key}" + (f"/{bkey}" if bkey else "") + f"/{sid}"
                    if path not in sources:
                        fails.append(f"fact without source: {path} = {str(val)[:60]}")

    # 3. Phone + desktop.
    from playwright.sync_api import sync_playwright
    shots = cdir / "shots"
    shots.mkdir(exist_ok=True)
    arabic = fill.get("lang", "ar") == "ar"
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, vp in (("phone", {"width": 390, "height": 844}), ("desktop", {"width": 1440, "height": 900})):
            ctx = b.new_context(viewport=vp, device_scale_factor=2 if name == "phone" else 1,
                                is_mobile=name == "phone", has_touch=name == "phone")
            pg = ctx.new_page()
            pg.goto(page_path.as_uri(), wait_until="networkidle", timeout=60000)
            # Lazy images inside side-scrolling carousels never enter the viewport: load them all now.
            pg.evaluate("""async () => { const imgs = [...document.images];
                imgs.forEach(i => { i.loading = 'eager'; if (i.src) i.src = i.src; });
                await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r;
                    setTimeout(r, 8000); }))); }""")
            pg.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
                window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }""")
            pg.wait_for_timeout(800)
            info = pg.evaluate("""() => ({
                broken: [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src')),
                images: document.images.length,
                sw: document.documentElement.scrollWidth, iw: window.innerWidth,
                dir: document.documentElement.getAttribute('dir'),
                noindex: !!document.querySelector('meta[name=robots][content*=noindex]'),
                links: [...document.querySelectorAll('a[href]')].map(a => a.href).filter(h => !h.startsWith('https://wa.me/')),
            })""")
            if info["broken"]:
                fails.append(f"{name}: images not loading: {info['broken'][:6]}")
            if info["sw"] > info["iw"] + 1:
                fails.append(f"{name}: page scrolls sideways ({info['sw']}px wide on a {info['iw']}px screen)")
            if arabic and info["dir"] != "rtl":
                fails.append(f"{name}: Arabic page without dir=rtl")
            if not info["noindex"]:
                fails.append(f"{name}: noindex meta missing")
            if info["links"]:
                fails.append(f"{name}: links not going to our WhatsApp: {info['links'][:4]}")
            notes.append(f"{name}: {info['images']} images, {info['sw']}px wide")
            if name == "phone":
                pg.screenshot(path=str(shots / "phone_top.jpg"), type="jpeg", quality=80)
            pg.screenshot(path=str(shots / f"{name}.jpg"), type="jpeg", quality=75, full_page=True)
            ctx.close()
        b.close()

    result = {"pass": not fails, "fails": fails, "notes": notes,
              "shots": [str(shots / f) for f in ("phone_top.jpg", "phone.jpg", "desktop.jpg")]}
    (cdir / "check.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in notes:
        print(n)
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    print("shots:", ", ".join(result["shots"]))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
