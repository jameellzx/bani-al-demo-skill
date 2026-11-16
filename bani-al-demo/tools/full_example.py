"""Look-only example: one demo with EVERY template section shown (not for clients, never published).

    python full_example.py <source slug> <new slug>

Takes the source demo's fill.json, shows the hidden sections too, fills their pictures with the client's
own photos and keeps the template's sample copy (cleaned: brand name, [needs proof] notes, ___ blanks).
"""
import json
import re
import shutil
import sys
import pathlib

DATA = pathlib.Path("C:/dev/bani-al-demo/clients")
TPL = pathlib.Path("C:/Users/user/Desktop/1st projet/قوالب/perfume-oud-store/slots.json")
FILL_BLANK = {"دقيقة": "15", "ساعة": "24", "ساعات": "8", "د.ك": "5"}


def clean(v, name):
    if not isinstance(v, str):
        return v
    if v.strip() == "أساس":
        return name
    v = re.sub(r"\s*\[يحتاج[^\]]*\]", "", v)
    v = re.sub(r"@___", "@a_kwt_b", v)

    def blank(m):
        after = v[m.end():m.end() + 8]
        for unit, num in FILL_BLANK.items():
            if unit in after:
                return num
        return "8"
    return re.sub(r"_{3,}", blank, v)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    s, d = DATA / src, DATA / dst
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    shutil.copytree(s / "ig", d / "ig")
    shutil.copy(s / "lead.json", d / "lead.json")
    fill = json.loads((s / "fill.json").read_text(encoding="utf-8"))
    page = json.loads((s / "page.json").read_text(encoding="utf-8"))
    name = page["name"]
    fill["hide"] = []
    photos = [p["image"] for p in page["products"]] + page["gram"]["images"] + [page["hero"]["image"], page["cta"]["image"]]
    photos += list(page.get("extra_photos") or [])  # hand-picked only
    photos = list(dict.fromkeys(photos))
    slots = json.loads(TPL.read_text(encoding="utf-8"))["slots"]
    hidden = {"categories", "oud", "home_scent", "gifts", "base", "quotes", "why", "old_way", "base_intro",
              "oud_detail", "home_detail", "proof", "offer", "newsletter"}
    k = 0
    for sl in slots:
        sec = sl["path"].split(":")[1].split("/")[0]
        if sl["group"] != "content" or sec not in hidden:
            continue
        p = sl["path"]
        if sl["type"] == "image_picker":
            fill["values"][p] = photos[k % len(photos)]
            k += 1
        elif p.endswith("_asset"):
            fill["values"][p] = ""
        elif p not in fill["values"]:
            fill["values"][p] = clean(sl["value"], name)
    # gifts = real products of the client
    for i, pr in enumerate(page["products"][:3], 1):
        b = f"index:gifts/gifts_{i}"
        fill["values"].update({f"{b}/title": pr["title"], f"{b}/image": pr["image"], f"{b}/vendor": pr.get("vendor", ""),
                               f"{b}/price": pr.get("price", ""), f"{b}/details": f"<p>{pr.get('details', '')}</p>"})
    fill["title"] = "مثال كامل - " + fill["title"]
    (d / "fill.json").write_text(json.dumps(fill, ensure_ascii=False, indent=1), encoding="utf-8")
    print("example fill:", d / "fill.json", "| photos used:", k)


if __name__ == "__main__":
    main()
