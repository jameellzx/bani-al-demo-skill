# Bani Al-Demo (باني الديمو) — demo websites for leads, from their own Instagram

A Claude Code skill that builds a **demo website for a prospective client** in about 10 minutes:

1. Picks a lead from the **الباحث** table (`الباحث.xlsx`, sheet «عملائي»), see [al-bahith-skill](https://github.com/jameellzx/al-bahith-skill).
2. You pick a template from your **قوالب** library, made by [shopify-clone-kit](https://github.com/jameellzx/shopify-clone-kit) (1.1.2+, every template has a `slots.json`).
3. Reads the client's Instagram in about 30 s (profile, logo, last 30 posts, every highlight) with your saved session, read only.
4. Builds a brand kit: colours from the logo and feed, Arabic font, tone of voice, products, real reviews.
5. Asks you about every gap (sections the Instagram can't fill).
6. Writes the page in the client's own language and voice. Optional sales copy from a [katib](https://github.com/jameellzx/katib-skill) research folder you name.
7. Checks it: no text, photo or colour left from the template, no invented facts (every price/review has a source), perfect on a phone (no sideways scroll, every image loads, right-to-left when Arabic).
8. After **your OK**, publishes it on GitHub Pages (`noindex`, robots blocked). Every button opens **your** WhatsApp with "I saw the demo for <client>". The link goes back into the Excel row.

## Requirements
- Claude Code, Python 3.11+, GitHub CLI (`gh auth login`)
- `pip install playwright openpyxl pillow python-liquid` then `playwright install chromium`
- shopify-clone-kit plugin 1.1.2+ and at least one template in قوالب
- al-bahith's Instagram session (`ig_profile.py --login`, you sign in yourself)

## Install
Paste this into Claude Code:
```
Install the Bani Al-Demo skill from https://github.com/jameellzx/bani-al-demo-skill:
copy the "bani-al-demo" folder into ~/.claude/skills/bani-al-demo.
Install: pip install playwright openpyxl pillow python-liquid, then playwright install chromium.
Check with: python ~/.claude/skills/bani-al-demo/scripts/paths.py --check
```
Then say **"باني الديمو"** or **"سوّ ديمو لـ <client>"**. The first run asks for your WhatsApp number and brand name
(saved only on your PC in `<data>/settings.json`).

## Your data
`~/bani-al-demo/` (or `config.json` → `{"data_dir": "..."}`, or env `BANI_DEMO_DATA`):
- `settings.json`: your WhatsApp number, brand name, folders (never in git)
- `clients/<slug>/`: `lead.json`, `ig/` (Instagram read + contact sheets), `client.json`, `gaps.md`, `fill.json`,
  `build/`, `site/` (the page), `shots/`, `check.json`, `published.json`
- `demos.md`: every published link

## Be careful
- The Pages repo is **public**: anyone with a link, or anyone browsing the repo, can see a demo. Pages carry `noindex` and
  robots.txt blocks crawlers, but that is not privacy. Remove a client's folder when they ask.
- Demos use the client's own photos and words to show them what their site could look like. Don't publish one without the
  user's OK, and never present it as the client's real site.
- Reading Instagram may break its terms. The script reads one profile per run, like a person browsing. Use at your own risk.

## Files
```
bani-al-demo/
  SKILL.md                   the workflow (10 steps, gates, rules)
  references/fill-guide.md   fill.json format, copy and photo rules
  scripts/paths.py           data folder + settings (--check, --set key=value)
  scripts/lead.py            find the lead in الباحث.xlsx (--list)
  scripts/ig_read.py         Instagram: profile, 30 posts, highlights, images (~30 s)
  scripts/sheet.py           contact sheets of posts/highlights + colour palette
  scripts/build.py           fill the template (slots.json), render with export_html.py, WhatsApp links + banner
  scripts/check.py           leftovers, facts, phone/desktop checks + screenshots
  scripts/publish.py         GitHub Pages repo, live link, Excel + demos.md
```
