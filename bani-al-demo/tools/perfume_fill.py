"""page.json -> fill.json for the perfume-oud-store template (short demo: hero, strip, products, FAQ, CTA, gallery).

    python perfume_fill.py <slug>

page.json (in the client folder) holds only the client's facts and the copy written from them:
{ "name", "title", "logo", "handle", "fonts": {...}, "colors": {"light","light2","accent","accent_dark","dark"},
  "nav": [...], "hero": {"heading","text","button","link2","image"}, "marquee": [...],
  "products_heading", "products_sub", "products": [{"title","vendor","details","image","price","source","badge"}],
  "faq_heading", "faq": [{"q","a"}], "cta": {"heading","text","button","link2","image"},
  "gram": {"heading","sub","images": [...]}, "sources": {...} }
Every section of the template that needs facts we don't have (reviews, oud tests, offers, gifts...) is hidden.
"""
import json
import re
from perfume_full_copy import SAFE
import sys
import pathlib

DATA = pathlib.Path("C:/dev/bani-al-demo/clients")
# plain field words the template also uses; they are the client's words too
GENERIC = ["العود", "العطور", "البخور", "عطور", "بخور", "عود", "مسك", "عنبر", "عطور رجالي", "عطور نسائي", "هدايا", "الهدايا", "المسك", "دهن العود", "السابق", "التالي", "الرئيسية", "للجنسين", "رجالي", "نسائي", "مباخر", "معمول", "المعمول", "دهن عود", "توصيل", "عطر", "ساعة"]
# user rule 2026-11-16: every section except «جرّب أول، ادفع بعدين» (offer)
KEEP = [x for x in ["hero", "marquee", "categories", "bestsellers", "oud", "home_scent", "gifts", "base", "quotes",
        "why", "old_way", "base_intro", "oud_detail", "home_detail", "proof", "faq", "final_cta", "gram", "newsletter"]]
ALL = ["hero", "marquee", "categories", "bestsellers", "oud", "home_scent", "gifts", "base", "quotes", "why", "old_way",
       "base_intro", "oud_detail", "home_detail", "proof", "offer", "faq", "final_cta", "gram", "newsletter"]


def html(t):
    t = (t or "").strip()
    if not t or t.startswith("<"):
        return t
    return "".join(f"<p>{line}</p>" for line in t.split("\n") if line.strip())


TPL_SLOTS = pathlib.Path("C:/Users/user/Desktop/1st projet/قوالب/perfume-oud-store/slots.json")


def full_sections(p, v, prods, c, sources):
    """Fill the extra sections: shared safe copy, the shop's own photos, gifts + home scent from its products.
    Returns the plain texts to allow in check.py (shared tips the template also uses)."""
    name = p["name"]
    extra = {"categories", "oud", "home_scent", "gifts", "base", "quotes", "why", "old_way", "base_intro", "oud_detail",
             "home_detail", "proof", "newsletter"}
    photos = [pr["image"] for pr in prods] + p["gram"]["images"] + [p["hero"]["image"], p["cta"]["image"]]
    # only photos picked by eye (page.json), never every post: a shop's feed can hold maps, flags, people, memes
    photos += list(p.get("extra_photos") or [])
    photos = list(dict.fromkeys(photos))
    k = 0
    for sl in json.loads(TPL_SLOTS.read_text(encoding="utf-8"))["slots"]:
        path = sl["path"]
        sec = path.split(":")[1].split("/")[0]
        if sl["group"] != "content" or sec not in extra or path in v:
            continue
        short = path.split(":", 1)[1]
        if sl["type"] == "image_picker":
            v[path] = photos[k % len(photos)]
            k += 1
        elif path.endswith("_asset") or sl["type"] == "url":
            v[path] = "" if sl["type"] != "url" else None
        elif path.endswith("_alt"):
            v[path] = name
        elif short in SAFE:
            v[path] = SAFE[short].replace("{name}", name)
        elif path.endswith(("previous_label",)):
            v[path] = "السابق"
        elif path.endswith(("next_label",)):
            v[path] = "التالي"
        elif sl["fact"]:
            v[path] = ""
        else:
            v[path] = sl["value"] if sl["value"] is None else re.sub(r"\s*\[يحتاج[^\]]*\]", "", str(sl["value"]))
    # gifts: three of the shop's own products; home scent: its last product
    gp = (prods[3:6] if len(prods) >= 6 else prods[:3]) or prods
    for i, pr in enumerate(gp[:3], 1):
        b = f"index:gifts/gifts_{i}"
        v.update({f"{b}/title": pr["title"], f"{b}/image": pr["image"], f"{b}/image_alt": pr["title"],
                  f"{b}/vendor": pr.get("vendor", ""), f"{b}/price": pr.get("price", ""), f"{b}/compare_price": "",
                  f"{b}/details": html(pr.get("details", "")), f"{b}/badge": "", f"{b}/proof_note": ""})
        if pr.get("price") and pr.get("source"):
            sources[f"{b}/price"] = pr["source"]
    hp = prods[-1]
    v.update({"index:home_scent/title": hp["title"], "index:home_scent/text": html(hp.get("details", "")),
              "index:home_scent/price": hp.get("price", ""), "index:home_scent/image": hp["image"]})
    if hp.get("price") and hp.get("source"):
        sources["index:home_scent/price"] = hp["source"]
    for i in range(1, 5):  # buyers' own words from the الكاتب research, not this shop's reviews
        sources[f"index:quotes/quotes_{i}/text"] = "مشروع-العطور/2-الكاتب/03-avatar-perfume.md"
    allow = []
    for t in SAFE.values():
        allow += [x.strip() for x in re.split(r"<[^>]+>", t.replace("{name}", name)) if x.strip()]
    return allow


def main():
    slug = sys.argv[1]
    c = DATA / slug
    p = json.loads((c / "page.json").read_text(encoding="utf-8"))
    col = p["colors"]
    light, light2, acc, accd = col["light"], col.get("light2", col["light"]), col["accent"], col.get("accent_dark", col["accent"])
    v = {}
    h = p["hero"]
    v.update({
        "index:hero/heading": h["heading"], "index:hero/text": html(h["text"]),
        "index:hero/button_label": h.get("button", "اطلب بالواتساب"), "index:hero/link2_label": h.get("link2", ""),
        "index:hero/image": h["image"], "index:hero/image_alt": p["name"],
        "index:marquee/aria_label": "عن المحل", "index:marquee/sep_image_alt": "", "index:marquee/sep_image_asset": "",
    })
    mq = p["marquee"][:4]
    for i, t in enumerate(mq, 1):
        v[f"index:marquee/marquee_{i}/text"] = t
    prods = p["products"][:6]
    v.update({"index:bestsellers/heading": p.get("products_heading", "من منتجاتنا"),
              "index:bestsellers/subheading": html(p.get("products_sub", "")),
              "index:bestsellers/price_note": "", "index:bestsellers/button_label": "",
              "index:bestsellers/button2_label": "", "index:bestsellers/footer_text": "",
              "index:bestsellers/previous_label": "السابق", "index:bestsellers/next_label": "التالي"})
    sources = dict(p.get("sources") or {})
    for i, pr in enumerate(prods, 1):
        k = f"index:bestsellers/bestsellers_{i}"
        v.update({f"{k}/image": pr["image"], f"{k}/image_alt": pr["title"], f"{k}/badge": pr.get("badge", ""),
                  f"{k}/vendor": pr.get("vendor", p["name"]), f"{k}/title": pr["title"],
                  f"{k}/details": html(pr.get("details", "")), f"{k}/price": pr.get("price", ""),
                  f"{k}/compare_price": "", f"{k}/proof_note": ""})
        if pr.get("price") and pr.get("source"):
            sources[f"{k}/price"] = pr["source"]
    faq = p["faq"][:10]
    v.update({"index:faq/heading": p.get("faq_heading", "أسئلة تتكرر"), "index:faq/subheading": ""})
    for i, f in enumerate(faq, 1):
        v.update({f"index:faq/faq_{i}/question": f["q"], f"index:faq/faq_{i}/answer": html(f["a"]),
                  f"index:faq/faq_{i}/proof_note": ""})
    ct = p["cta"]
    v.update({"index:final_cta/badge_text": ct.get("badge", ""), "index:final_cta/heading": ct["heading"],
              "index:final_cta/text": html(ct["text"]), "index:final_cta/button_label": ct.get("button", "اطلب الحين"),
              "index:final_cta/link2_label": ct.get("link2", ""), "index:final_cta/image": ct["image"],
              "index:final_cta/image_alt": p["name"]})
    g = p["gram"]
    imgs = g["images"][:5]
    v.update({"index:gram/heading": g.get("heading", "تابعنا على انستقرام"),
              "index:gram/subheading": html(g.get("sub", "")),
              "index:gram/previous_label": "السابق", "index:gram/next_label": "التالي"})
    for i, im in enumerate(imgs, 1):
        v.update({f"index:gram/gram_{i}/image": im, f"index:gram/gram_{i}/image_alt": p["name"]})
    allow = full_sections(p, v, prods, c, sources)
    v.update(p.get("extra_values") or {})
    cmap = {}
    for x in ["#FFE3D7", "#FFECE1", "#FFF4E8", "#FFF5E5", "#E6E6FA"]:
        cmap[x] = light
    for x in ["#F5F5DC", "#E5DCCB"]:
        cmap[x] = light2
    for x in ["#F4C2C2", "#FF9494", "#FF7C7C"]:
        cmap[x] = acc
    for x in ["#B4532A", "#B9AC8A"]:
        cmap[x] = accd
    fill = {
        "template": "perfume-oud-store", "shop_name": p["name"], "title": p["title"], "logo": p["logo"],
        "lang": "ar", "dir": "rtl", "nav": p.get("nav", ["الرئيسية", "منتجاتنا", "تواصل"]),
        "fonts": p.get("fonts", {"heading": "tajawal_n8", "body": "tajawal_n4"}),
        "color_map": cmap,
        "hide": [f"index:{s}" for s in ALL if s not in KEEP],
        "blocks": {
            "index:marquee": {"order": [f"marquee_{i}" for i in range(1, len(mq) + 1)]},
            "index:bestsellers": {"order": [f"bestsellers_{i}" for i in range(1, len(prods) + 1)]},
            "index:faq": {"order": [f"faq_{i}" for i in range(1, len(faq) + 1)]},
            "index:gram": {"order": [f"gram_{i}" for i in range(1, len(imgs) + 1)]},
        },
        "values": v, "sources": sources, "allow_text": GENERIC + allow + p.get("allow_text", []),
        "allow_colors": p.get("allow_colors", []), "extra_css": ".ck-marquee__sep svg,.ck-marquee__sep img{display:none!important}.ck-proof:empty,.ck-btn:empty{display:none!important}.ck-marquee__sep::before{content:\"✦\";font-size:14px;opacity:.7}" + p.get("extra_css", ""),
    }
    (c / "fill.json").write_text(json.dumps(fill, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fill.json written:", len(v), "values")


if __name__ == "__main__":
    main()
