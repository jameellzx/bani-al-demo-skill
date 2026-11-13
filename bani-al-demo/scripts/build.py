"""Build a client's demo page from a template + <client>/fill.json (format: references/fill-format.md).

    python build.py <slug>

Steps: copy the template's sections and page JSON to <client>/build/, repaint template colours (color_map) in
the settings AND in the sections' CSS, set fonts, add/remove/reorder blocks, hide sections, write every value,
copy + shrink the client's images into <client>/site/images/, render with shopify-clone-kit's export_html.py,
then point every link at our WhatsApp and add the demo banner. Output: <client>/site/index.html
"""
from __future__ import annotations

import copy
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

from PIL import Image

from paths import check, client_dir, settings

SCHEMA_RE = re.compile(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}", re.S)
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
# Right-to-left: text alignment settings are physical (text-align: left) so they are swapped; position
# settings are usually flexbox (flex-start already follows dir=rtl) so they are left alone.
SIDE_RE = re.compile(r"text_align|alignment", re.I)
CSS_ALIGN_RE = re.compile(r"text-align:\s*(left|right)\b")
MIRROR = {"left": "right", "right": "left"}
# Always added: the demo header must fit a phone (shop name on one line, menu scrolls sideways).
DEMO_CSS = """
.ck-demo-header { gap: 12px; }
.ck-demo-header strong { white-space: nowrap; font-size: 18px; }
@media (max-width: 700px) {
  .ck-demo-header { padding: 12px 4%; }
  .ck-demo-header nav { gap: 14px; font-size: 13px; overflow-x: auto; white-space: nowrap; }
}
"""


def load(path):
    return json.loads(open(path, encoding="utf-8-sig").read())


def save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def shrink(src, dst, max_side=1600):
    im = Image.open(src)
    im = im.convert("RGB") if im.mode not in ("RGB",) else im
    im.thumbnail((max_side, max_side))
    im.save(dst, "JPEG", quality=80, optimize=True, progressive=True)


def wa_link(s, client):
    text = s["wa_message"].format(client=client)
    return f"https://wa.me/{s['whatsapp']}?text={urllib.parse.quote(text)}"


def banner_html(s, client, link):
    brand = html.escape(s["brand_name"])
    text = html.escape(s["banner_text"].format(client=client))
    return f"""<div class="bd-banner" dir="rtl" lang="ar">
  <span>{text}</span>
  <a href="{link}" target="_blank" rel="noopener">واتساب {brand}</a>
</div>
<style>
  body {{ padding-bottom: 64px; }}
  .bd-banner {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 9999; display: flex; gap: 12px;
    align-items: center; justify-content: center; padding: 10px 14px; background: rgba(17,17,17,.94); color: #fff;
    font: 14px/1.4 Tahoma, "Segoe UI", sans-serif; }}
  .bd-banner a {{ background: #25D366; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 999px;
    white-space: nowrap; font-weight: 700; }}
  @media (max-width: 600px) {{ .bd-banner {{ font-size: 12px; }} }}
</style>
"""


def sections_of(doc):
    return doc.get("sections", doc)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    slug = sys.argv[1]
    s = settings()
    miss = [m for m in check() if m.startswith(("whatsapp", "brand_name", "clone_kit"))]
    if miss:
        sys.exit("SETTINGS_MISSING\n" + "\n".join(miss))
    cdir = client_dir(slug)
    fill = load(cdir / "fill.json")
    tdir = os.path.join(s["templates_dir"], fill["template"])
    slots = load(os.path.join(tdir, "slots.json"))
    bdir, site = cdir / "build", cdir / "site"
    for d in (bdir, site):
        shutil.rmtree(d, ignore_errors=True)
    (bdir / "templates").mkdir(parents=True)
    (site / "images").mkdir(parents=True)

    # Sections: copy and repaint hard-coded template colours in their CSS.
    cmap = {k.upper(): v for k, v in (fill.get("color_map") or {}).items()}
    rtl = fill.get("dir") == "rtl"
    shutil.copytree(os.path.join(tdir, "sections"), bdir / "sections")
    rx = re.compile("|".join(re.escape(k) for k in cmap), re.I) if cmap else None
    for f in glob.glob(str(bdir / "sections" / "*.liquid")):
        src = open(f, encoding="utf-8").read()
        if rx:
            src = rx.sub(lambda m: cmap[m.group(0).upper()], src)
        if rtl:  # hard-coded text-align: left/right -> start/end (same as before on left-to-right pages)
            src = CSS_ALIGN_RE.sub(lambda m: "text-align: " + ("start" if m.group(1) == "left" else "end"), src)
        open(f, "w", encoding="utf-8", newline="\n").write(src)
    shutil.copy(os.path.join(tdir, "template.json"), bdir / "template.json")

    docs = {}
    for name in ("index", "footer-section"):
        p = os.path.join(tdir, "templates", name + ".json")
        if os.path.exists(p):
            docs[name] = load(p)

    def target(file, section, block=None):
        sec = sections_of(docs[file])[section]
        if block is None:
            return sec.setdefault("settings", {})
        return sec["blocks"][block].setdefault("settings", {})

    # 1. Colours, fonts and (right-to-left pages) mirrored alignment on every existing slot.
    #    Made explicit, so cloned blocks inherit them; fill.json values still win later.
    fonts = fill.get("fonts") or {}
    mirror = fill.get("mirror", fill.get("dir") == "rtl")
    for sl in slots["slots"]:
        if sl["file"] not in docs:
            continue
        val = sl["value"]
        if mirror and sl["type"] == "select" and SIDE_RE.search(sl["setting_id"]) and val in MIRROR:
            target(sl["file"], sl["section"], sl["block"])[sl["setting_id"]] = MIRROR[val]
        if sl["type"] in ("color", "color_background") and isinstance(val, str) and val.upper() in cmap:
            target(sl["file"], sl["section"], sl["block"])[sl["setting_id"]] = cmap[val.upper()]
        elif sl["type"] == "font_picker" and fonts:
            key = "heading" if re.search(r"head|title", sl["setting_id"] + str(sl["label"]), re.I) else "body"
            if fonts.get(key):
                target(sl["file"], sl["section"], sl["block"])[sl["setting_id"]] = fonts[key]

    # 2. Blocks: new ones copy an existing block, then the order list decides what stays.
    for loc, spec in (fill.get("blocks") or {}).items():
        file, section = loc.split(":", 1)
        sec = sections_of(docs[file])[section]
        for new_key, from_key in (spec.get("new") or {}).items():
            sec["blocks"][new_key] = copy.deepcopy(sec["blocks"][from_key])
        order = spec["order"]
        sec["block_order"] = order
        sec["blocks"] = {k: v for k, v in sec["blocks"].items() if k in order}

    # 3. Hide sections.
    for loc in fill.get("hide") or []:
        file, section = loc.split(":", 1)
        sections_of(docs[file])[section]["disabled"] = True

    # 4. Values. Local image files are shrunk into site/images and referenced like Shopify files.
    n_img = 0
    for loc, val in (fill.get("values") or {}).items():
        file, rest = loc.split(":", 1)
        parts = rest.split("/")
        section, sid = parts[0], parts[-1]
        block = parts[1] if len(parts) == 3 else None
        if isinstance(val, str) and val.lower().endswith(IMG_EXT) and not val.startswith("shopify://"):
            src = cdir / val
            if not src.exists():
                sys.exit(f"IMAGE_MISSING {loc}: {src}")
            n_img += 1
            name = f"c{n_img:02d}-{section}{'-' + block if block else ''}-{sid}.jpg".replace("_", "-")
            shrink(src, site / "images" / name)
            val = f"shopify://shop_images/{name}"
        target(file, section, block)[sid] = val

    save(bdir / "templates" / "index.json", docs["index"])
    if "footer-section" in docs:
        save(bdir / "templates" / "footer-section.json", docs["footer-section"])

    # Logo + banner, then render with the clone kit.
    client = fill.get("shop_name") or slug
    link = wa_link(s, client)
    args = []
    if fill.get("logo"):
        shrink(cdir / fill["logo"], site / "images" / "logo.jpg", 400)
        args += ["--logo", str(site / "images" / "logo.jpg")]
    (bdir / "banner.html").write_text(banner_html(s, client, link), encoding="utf-8")
    exporter = os.path.join(s["clone_kit_scripts"], "export_html.py")
    cmd = [sys.executable, exporter, str(bdir), "--out", str(site / "index.html"), "--images", str(site / "images"),
           "--title", fill.get("title") or client, "--shop-name", client,
           "--nav", "|".join(fill.get("nav") or []) or "Home|Shop|Contact",
           "--lang", fill.get("lang", "ar"), "--noindex", "--body-end-html", str(bdir / "banner.html")] + args
    if fill.get("dir"):
        cmd += ["--dir", fill["dir"]]
    if fill.get("currency"):
        cmd += ["--currency", fill["currency"]]
    subprocess.run(cmd, check=True)

    # Every link opens our WhatsApp.
    page = open(site / "index.html", encoding="utf-8").read()

    def relink(m):
        tag = re.sub(r'\s(href|target|rel)="[^"]*"', "", m.group(0))
        return tag[:-1] + f' href="{html.escape(link)}" target="_blank" rel="noopener">'
    page = re.sub(r"<a\b[^>]*>", relink, page)
    page = page.replace("</head>", f"<style>{DEMO_CSS}{fill.get('extra_css') or ''}</style>\n</head>", 1)
    open(site / "index.html", "w", encoding="utf-8", newline="\n").write(page)
    print(f"built {site / 'index.html'} | {n_img} client images | links -> wa.me/{s['whatsapp']}")


if __name__ == "__main__":
    main()
