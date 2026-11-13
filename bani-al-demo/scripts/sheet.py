"""Contact sheets of a client's Instagram, so Claude can look at everything in a few images, plus colours.

    python sheet.py <slug>

Writes in <data>/clients/<slug>/ig/:
  sheet_posts.jpg        every post's images, labelled p01_1, p01_2 … (6 per row)
  sheet_highlights.jpg   every highlight story, labelled h01_03 …, a title row per highlight
  palette.json           main colours of the logo and of the most-liked posts (hex, share, neutral yes/no)
Prints the palette and the sheet paths.
"""
from __future__ import annotations

import colorsys
import json
import sys

from PIL import Image, ImageDraw, ImageFont

from paths import client_dir

THUMB = 220


def font(size):
    for f in ("arial.ttf", "segoeui.ttf", "tahoma.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def thumb(path, w=THUMB, h=THUMB):
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        im = Image.new("RGB", (w, h), (230, 230, 230))
    im.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), (245, 245, 245))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def grid(cells, cols, w, h, out, rows_title=None):
    """cells: list of (label, path) or ("#title", text) for a full-width title row."""
    f, ft = font(16), font(20)
    rows, row = [], []
    for c in cells:
        if c[0] == "#title":
            if row:
                rows.append(row)
                row = []
            rows.append(c)
            continue
        row.append(c)
        if len(row) == cols:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    label_h, title_h = 24, 34
    height = sum(title_h if isinstance(r, tuple) else h + label_h for r in rows)
    sheet = Image.new("RGB", (cols * w, max(height, 1)), "white")
    d = ImageDraw.Draw(sheet)
    y = 0
    for r in rows:
        if isinstance(r, tuple):
            d.rectangle([0, y, cols * w, y + title_h], fill=(30, 30, 30))
            d.text((10, y + 6), r[1], fill="white", font=ft)
            y += title_h
            continue
        for i, (label, path) in enumerate(r):
            sheet.paste(thumb(path, w, h), (i * w, y))
            d.rectangle([i * w, y + h, (i + 1) * w, y + h + label_h], fill=(255, 255, 255))
            d.text((i * w + 6, y + h + 3), label, fill="black", font=f)
        y += h + label_h
    sheet.save(out, quality=82)
    return out


def palette(paths, n=6):
    counts = {}
    for p in paths:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        im.thumbnail((120, 120))
        q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()
        for cnt, idx in q.getcolors():
            r, g, b = pal[idx * 3: idx * 3 + 3]
            key = (r // 12 * 12, g // 12 * 12, b // 12 * 12)
            counts[key] = counts.get(key, 0) + cnt
    total = sum(counts.values()) or 1
    out = []
    for (r, g, b), cnt in sorted(counts.items(), key=lambda kv: -kv[1])[: n * 3]:
        hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hexc = "#%02X%02X%02X" % (r, g, b)
        if any(sum(abs(int(hexc[i:i + 2], 16) - int(o["hex"][i:i + 2], 16)) for i in (1, 3, 5)) < 40 for o in out):
            continue  # too close to a colour already listed
        out.append({"hex": hexc, "share": round(cnt / total, 3), "neutral": sat < 0.18 or light < 0.08 or light > 0.94})
        if len(out) >= n:
            break
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    slug = sys.argv[1]
    ig = client_dir(slug) / "ig"
    posts = json.loads((ig / "posts.json").read_text(encoding="utf-8"))
    hls = json.loads((ig / "highlights.json").read_text(encoding="utf-8"))

    cells = [("logo", ig / "media" / "logo.jpg")]
    for p in posts:
        for f in p["files"]:
            cells.append((f.split("/")[-1][:-4], ig / f))
    a = grid(cells, 6, THUMB, THUMB, ig / "sheet_posts.jpg")

    cells = []
    for h in hls:
        cells.append(("#title", f"h{h['n']:02d}  {h.get('title') or ''}  ({len(h['stories'])} stories)"))
        for s in h["stories"]:
            cells.append((s["file"].split("/")[-1][:-4], ig / s["file"]))
    b = grid(cells, 8, 150, 266, ig / "sheet_highlights.jpg") if cells else None

    top = sorted(posts, key=lambda p: -(p.get("likes") or 0))[:8]
    pal = {"logo": palette([ig / "media" / "logo.jpg"], 4),
           "feed": palette([ig / p["files"][0] for p in top if p["files"]], 8)}
    (ig / "palette.json").write_text(json.dumps(pal, indent=1), encoding="utf-8")
    print("posts sheet:", a)
    print("highlights sheet:", b)
    for k, v in pal.items():
        print(k, " ".join(f"{c['hex']}({c['share']:.0%}{',n' if c['neutral'] else ''})" for c in v))


if __name__ == "__main__":
    main()
