# fill.json: how to fill a template for a client

`<data>/clients/<slug>/fill.json` tells `build.py` what to change in the template. The template's
`slots.json` (in قوالب/<template>/) lists every setting you can change.

## Read slots.json first
- `slots[]`: `path` (`index:hero/slide_1/heading`, `footer-section:ck_footer/menu_1/title`), `type`, `group`,
  `label`, `value` (the template's value), `fact`.
  - `group: content` = text, images, links: change ALL of these (leftovers fail the check).
  - `group: brand` = colours and fonts: use `color_map` and `fonts` instead of one by one.
  - `group: layout` = sizes, toggles, positions: leave alone unless something looks wrong.
- `sections[]`: section keys, block order, which block types can repeat.
- `leftovers`: the template's own text, image names and colours. None may stay on the page.

Quick list of the content slots:
```
python -c "import json;d=json.load(open(r'<template>/slots.json',encoding='utf-8'));[print(s['path'],s['type'],'|',str(s['value'])[:50],'| FACT' if s['fact'] else '') for s in d['slots'] if s['group']=='content']"
```

## Format
```json
{
  "template": "baby-bath-store",
  "shop_name": "نور بن شنان",                 // shown in the header, banner, page title
  "title": "نور بن شنان | عبايات وبليزرات",
  "logo": "ig/media/logo.jpg",               // paths are relative to the client folder
  "lang": "ar", "dir": "rtl",                // from the client's Instagram language; "en"/"ltr" for English
  "nav": ["الرئيسية", "العبايات", "تواصل"],
  "currency": "KWD ",                        // only if a template prints money itself
  "fonts": {"heading": "tajawal_n8", "body": "tajawal_n4"},
  "color_map": {"#F9DE6E": "#E9E4DC"},       // every colour in leftovers.colors -> a client colour
  "hide": ["index:press", "index:reviews"],  // sections we can't fill with real content (user decides)
  "blocks": {                                // optional: change how many cards/products/slides
    "index:bestsellers": {"order": ["demo_1", "demo_2", "new_7"], "new": {"new_7": "demo_2"}}
  },
  "values": { "<slot path>": "<value>" },    // text, richtext (<p>…</p>), numbers, colours, image paths
  "sources": { "<fact slot path>": "https://www.instagram.com/p/…/" },
  "allow_text": [], "allow_colors": [],      // only for things that are really the client's (rare)
  "extra_css": ""                            // last resort for a layout problem
}
```

Rules that `build.py` applies by itself:
- An image value that is a local file (`ig/media/p03_1.jpg`) is shrunk to 1600 px and copied into `site/images/`.
- `dir: rtl` swaps text-alignment settings left<->right and turns hard-coded `text-align: left` into `start`.
- `color_map` repaints settings AND the CSS inside the copied sections.
- A new block (`new`) copies every setting of the block it copies, including fake prices and review counts:
  set all of its content and fact slots in `values` (the check fails otherwise).
- Every link on the page goes to our WhatsApp; the demo banner is added at the bottom.

## Arabic fonts (Google Fonts)
`tajawal`, `cairo`, `almarai`, `ibm_plex_sans_arabic`, `noto_kufi_arabic`, `noto_naskh_arabic`, `readex_pro`,
written as `<name>_n4` (normal) / `_n7` (bold) / `_n8` (extra bold). Match the client's feel: Tajawal or Almarai
for clean and modern, Noto Naskh for classic, Cairo for bold and friendly.

## Writing the copy
- **Language and voice from Instagram.** The client's own dialect, words, emoji habits and how formal they are.
  Reuse their phrases (they wrote "رزه وكشخه", so the page says it too). Short lines, like their captions.
- **Main content = Instagram.** Product names exactly as they post them ("Code : Royal Blazer" -> Royal Blazer),
  what they say about each piece, delivery, how to order, colours, sizes.
- **Sales copy from الكاتب only when the user named a research folder.** Use its avatar (pains, wants, words),
  offer brief (big idea, promise) and beliefs for the hero promise, benefits and objection lines. Never take
  its reviews, numbers, guarantees or founder story: those are not this client's.
- **Facts only from a source.** Price, rating, review count, number of customers, press, guarantee, "best
  seller" claims: only if the client posted it; put the post link in `sources`. Unknown -> empty value
  (price ""), rating 0, or hide the section. Customer reviews: only real ones (e.g. a «رأي العميل» highlight),
  quoted as written, name only as shown; put the story file or post link in `sources`.
- **Pictures.** Best-lit, product-first photos; hero = the strongest wide or tall product shot. For slots where
  text sits on top of the photo (hero, promo), avoid photos that already have words on them. Video posts
  give a cover frame (`type: video`): fine for cards, weaker for the hero.
- **Readable text on photos.** Dark photo -> white text + overlay (hero `overlay_opacity` 30-45,
  `slide_text_color`/`slide_heading_color` #FFFFFF, light button). Check `shots/phone_top.jpg`.
- Accessibility labels (`previous_label`, `aria_label` …) are content too: translate them.
