---
name: bani-al-demo
description: باني الديمو / مصنع الديمو (the demo builder). Builds a demo website for a prospective client found by الباحث - takes a template from قوالب (shopify-clone-kit), fills it with the client's own Instagram (logo, name, photos, products, tone of voice), adds sales copy from a الكاتب research folder when the user names one, checks it (no template leftovers, only real facts, perfect on a phone), and after the user's OK publishes it on GitHub Pages (noindex) with every button opening our WhatsApp. The link goes into الباحث.xlsx. Use when the user says "باني الديمو", "مصنع الديمو", "سوّ ديمو", "سوي ديمو لـ", "ابني ديمو", "demo for <client>", "build a demo", "demo page", or picks a lead and wants a preview site for it. One client per run.
---

# باني الديمو (bani-al-demo)

Talk to the user in Arabic (Gulf, plain words). Scripts: `~/.claude/skills/bani-al-demo/scripts/` (`scripts/…` below;
use the full path). Run them with the system `python`. Data folder: `python scripts/paths.py` prints it
(`config.json` in this skill, or env `BANI_DEMO_DATA`). Client folder: `<data>/clients/<slug>/`.
Needs: `pip install playwright openpyxl pillow python-liquid`, `playwright install chromium`, the
shopify-clone-kit plugin (1.1.2+, for `slots.json` and `export_html.py` flags), al-bahith's Instagram session, `gh` signed in.

## 0. Settings (first run)
`python scripts/paths.py --check`. If `whatsapp` or `brand_name` is missing, ask the user once:
«شنو رقم الواتساب اللي تبي الأزرار تفتحه، وشنو الاسم اللي يطلع على شريط الديمو؟» then
`python scripts/paths.py --set whatsapp=965XXXXXXXX "brand_name=..."`. Kept only in `<data>/settings.json`, never in git.

## 1. Client
User names a lead (name, @handle or link). `python scripts/lead.py "<it>"` → `slug` + `lead.json`.
`--list` shows every lead. `MATCHES` → ask which one. `NOT_FOUND` → ask for the Instagram handle.
A lead that already has «الموقع التجريبي» → ask: update the old demo (same link) or stop.

## 2. Template
List the folders in `<templates_dir>` (قوالب): name, `title` from `template.json`, sections, and show `preview-0-html.jpg`.
The user picks; never pick for them. No `slots.json` in it → `python <clone_kit_scripts>/save_template.py --slots-only <template>`.

## 3. الكاتب research (user rule, 2026-11-16)
**Instagram is the source of truth; الكاتب is how it gets written.** Every fact on the page (products, prices, delivery,
branches, reviews, the brand's own words) comes from the client's Instagram. Then rewrite those facts better with the
الكاتب method: the buyer's own words, the avatar's wants and fears, the core beliefs and the offer angle from the
الكاتب files for that field. الكاتب never adds a fact the client did not post (no invented guarantees, numbers or claims).
Find the الكاتب folder for the field: a project folder like `<project>/2-الكاتب` (e.g. مشروع-العطور), or one in
`<katib_dir>`. Ask only if there is none or more than one fits: «في بحث من الكاتب لنفس المجال؟». Read at least the
avatar, beliefs and website-copy files before writing `fill.json`.

## 4. Read Instagram (~30 s)
`python scripts/ig_read.py <handle> --slug <slug>` → `ig/profile.json`, `posts.json` (30), `highlights.json`, `media/`.
Opens the profile like a person (al-bahith's session), so never run it while al-bahith reads Instagram.
- `NO_SESSION` / `LOGIN_WALL`: «لازم تسجل دخول انستقرام مرة وحدة بنفسك» → `python ~/.claude/skills/al-bahith/scripts/ig_profile.py --login`
  (the user types their own password, never Claude). Then run again.
- `HAS_SITE <url>` (also `ig/has_site.txt`): the client already has a working website, found in the bio, a link hub,
  the email domain or **the post captions** (many shops write their site only under each post). Stop: no demo for a
  lead with a working site. Tell the user and mark the lead in الباحث.xlsx (عنده موقع؟ = نعم).
- `RATE_LIMIT`: stop, tell the user, try later. `PARSE_FAIL`: Instagram changed its page; fix `profile_object` /
  the embedded keys in `ig_read.py` and say so.

## 5. Brand kit
`python scripts/sheet.py <slug>` → `ig/sheet_posts.jpg`, `ig/sheet_highlights.jpg`, `ig/palette.json`. Look at both sheets and
read every caption and highlight title. Write `<client>/client.json`:
name (Arabic + Latin as they write it), logo file, colours (2-4 from the logo/feed, with a light background and a dark text
colour), font pick, language + dialect, tone (formality, emoji, repeated phrases), products (name, what they say about it,
colours, price only if posted, photo files, source post link), contact facts from the bio (delivery, how to order), real
customer reviews (only from posts/highlights, with the file), the best photos with their role (hero, product, lifestyle).

## 6. Gaps (ask, every time)
Compare the template's content slots (`slots.json`, see `references/fill-guide.md`) with `client.json`. Write `gaps.md` and ask
the user about each gap in one message, with options: repeat one of their photos / stock photo / AI image (cost asked first) /
hide the section. Typical gaps: founder story, press logos, reviews, prices, guides. Wait for the answers.

## 7. Fill
Write `<client>/fill.json` exactly as `references/fill-guide.md` says (read it every run): every content slot, `color_map` for
every leftover colour, fonts, hidden sections, block counts, `sources` for every fact slot used.

## 8. Build + check
`python scripts/build.py <slug>` then `python scripts/check.py <slug>`. Check FAIL → fix `fill.json`, build, check again.
Check PASS → still look at `shots/phone_top.jpg`, `shots/phone.jpg` and `shots/desktop.jpg` yourself: text readable on
photos, nothing cut or overlapping, photos fit their boxes, Arabic reads right to left, nothing from the template's old
subject. Fix and rebuild until it looks like the client's own site.

## 9. User approval (gate)
Show the user the phone and desktop screenshots (and the local `site/index.html`). Say what was hidden and why.
**Nothing is published without the user's OK.** Changes → back to step 7.

## 10. Publish
`python scripts/publish.py <slug>` (only after the OK; it refuses if the last build has not passed `check.py`).
First time it creates the public repo `<github_user>/<pages_repo>` with GitHub Pages, robots.txt blocking crawlers and an
empty root page. Prints the link; writes «الموقع التجريبي» and «تاريخ الديمو» in الباحث.xlsx and a line in `<data>/demos.md`.
- `EXCEL_LOCKED`: ask the user to close الباحث.xlsx, then run publish again (same link).
- `NOT_LIVE_YET`: GitHub Pages is still building; the link works in a few minutes.
Give the user the link and remind them: the repo is public, so anyone with the link (or browsing the repo) can see it.

## Rules
- Only the client's real content. No invented prices, ratings, review counts, customer numbers, press or guarantees.
- No template leftovers: no text, photo, name or colour from the template's original store.
- The page must be perfect on a phone; most clients open the link from an Instagram DM.
- One client per run. Read-only on Instagram. Never message the client; the user sends the link.
