"""Read one client's Instagram fast: profile, logo, last ~30 posts, all highlights. Read only.

Uses al-bahith's saved Instagram session (headless Chromium). Opens the profile like a person would and keeps the
JSON Instagram's own page loads: profile, first 12 posts and the highlight list are embedded in the profile page;
scrolling loads more posts; each highlight's own page holds its stories (3 opened at a time). Direct calls to
Instagram's API (web_profile_info, feed/user) answered 429 on 2026-11-13, so they are not used.
Images then download in parallel over plain HTTP.

    python ig_read.py <handle> [--slug SLUG] [--posts 30] [--max-highlights 40]

Writes <data>/clients/<slug>/ig/: profile.json, posts.json, highlights.json, media/ (logo.jpg, p01_1.jpg …,
h01_cover.jpg, h01_03.jpg …). Prints a summary and the seconds taken.
Status words (printed alone when it stops): NO_SESSION, LOGIN_WALL, RATE_LIMIT, NOT_FOUND, PARSE_FAIL.
Never run it while al-bahith's ig_profile.py is running (same session folder).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from paths import client_dir, settings, slugify

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")
POSTS_QUERY = "PolarisProfilePostsTabContentQuery"
TIMELINE_KEY = "xdt_api__v1__feed__user_timeline_graphql_connection"
REELS_KEY = "xdt_api__v1__feed__reels_media__connection"


class Stop(Exception):
    pass


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def best_image(item, min_width=1080):
    """Smallest version at least 1080 px wide (enough for a web page, about half the bytes of the original)."""
    c = ((item or {}).get("image_versions2") or {}).get("candidates") or []
    if not c:
        return ""
    big = [x for x in c if (x.get("width") or 0) >= min_width]
    return min(big, key=lambda x: x.get("width") or 0)["url"] if big else c[0]["url"]


def embedded(html, key):
    """First JSON value that follows "key": in the page's embedded data."""
    m = re.search('"%s":' % re.escape(key), html)
    if not m:
        return None
    try:
        return json.JSONDecoder().raw_decode(html, m.end())[0]
    except Exception:
        return None


def profile_object(html, handle):
    """The profile's own user object inside the page's embedded JSON (same idea as al-bahith)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r'"user":\{', html):
        try:
            obj, _ = dec.raw_decode(html, m.start() + 7)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("username", "").lower() == handle.lower() and "biography" in obj:
            return obj
    return None


def highlight_tray(html):
    dec = json.JSONDecoder()
    for m in re.finditer(r'"highlights":', html):
        try:
            o = dec.raw_decode(html, m.end())[0]
        except Exception:
            continue
        if isinstance(o, dict) and o.get("edges"):
            return [e["node"] for e in o["edges"] if str((e.get("node") or {}).get("id", "")).startswith("highlight:")]
    return []


def check_page(page, html):
    if "accounts/login" in page.url or "/challenge" in page.url:
        raise Stop("LOGIN_WALL")
    if "Please wait a few minutes" in html[:20000]:
        raise Stop("RATE_LIMIT")


def post_record(n, it):
    media = it.get("carousel_media") or [it]
    images = [best_image(m) for m in media if best_image(m)]
    cap = (it.get("caption") or {}).get("text") or ""
    return {
        "n": n, "code": it.get("code"), "url": f"https://www.instagram.com/p/{it.get('code')}/",
        "taken_at": it.get("taken_at"),
        "type": {1: "image", 2: "video", 8: "carousel"}.get(it.get("media_type"), "other"),
        "caption": cap, "likes": it.get("like_count"), "comments": it.get("comment_count"),
        "location": (it.get("location") or {}).get("name"),
        "accessibility_caption": it.get("accessibility_caption"),
        "image_urls": images, "files": [f"media/p{n:02d}_{i}.jpg" for i in range(1, len(images) + 1)],
    }


def story_record(h, i, it):
    stickers = []
    for k in ("story_link_stickers", "story_cta", "story_hashtags", "story_locations", "story_questions",
              "story_feed_media"):
        if it.get(k):
            stickers.append({k: it[k]})
    return {"n": i, "taken_at": it.get("taken_at"), "type": "video" if it.get("media_type") == 2 else "image",
            "image_url": best_image(it), "file": f"media/h{h:02d}_{i:02d}.jpg",
            "accessibility_caption": it.get("accessibility_caption"), "stickers": stickers}


def profile_record(u, handle):
    return {
        "id": u.get("id") or u.get("pk"), "username": u.get("username"), "full_name": u.get("full_name"),
        "biography": u.get("biography"), "external_url": u.get("external_url"),
        "bio_links": [l.get("url") for l in (u.get("bio_links") or []) if l.get("url")],
        "category": u.get("category") or u.get("category_name"),
        "followers": u.get("follower_count") or (u.get("edge_followed_by") or {}).get("count"),
        "posts_total": u.get("media_count"),
        "is_business": u.get("is_business") or u.get("is_business_account"),
        "business_email": u.get("public_email") or u.get("business_email"),
        "business_phone": u.get("public_phone_number") or u.get("contact_phone_number"),
        "logo_url": (u.get("hd_profile_pic_url_info") or {}).get("url") or u.get("profile_pic_url_hd")
                    or u.get("profile_pic_url"),
        "logo_file": "media/logo.jpg", "url": f"https://www.instagram.com/{handle}/",
    }


async def read(handle, want_posts, max_hl, parallel=3):
    from playwright.async_api import async_playwright
    state = pathlib.Path(settings()["ig_state"])
    if not state.exists():
        raise Stop("NO_SESSION")
    out = {"profile": None, "posts": [], "highlights": []}
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(str(state), headless=True,
                                                          viewport={"width": 1280, "height": 900})
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            more = []

            async def on_resp(r):
                if "graphql" in r.url and POSTS_QUERY in (r.request.post_data or ""):
                    try:
                        conn = (json.loads(await r.text()).get("data") or {}).get(TIMELINE_KEY) or {}
                        more.extend(e["node"] for e in conn.get("edges") or [])
                    except Exception:
                        pass
            page.on("response", on_resp)

            resp = await page.goto(f"https://www.instagram.com/{handle}/", wait_until="domcontentloaded",
                                   timeout=45000)
            await page.wait_for_timeout(3500)
            html = await page.content()
            check_page(page, html)
            u = profile_object(html, handle)
            if not u:
                if (resp and resp.status == 404) or "Page Not Found" in html[:5000]:
                    raise Stop("NOT_FOUND")
                raise Stop("PARSE_FAIL")
            out["profile"] = profile_record(u, handle)

            # Posts: 12 embedded, then scroll until enough arrive.
            tl = embedded(html, TIMELINE_KEY) or {}
            items = [e["node"] for e in tl.get("edges") or []]
            has_next = (tl.get("page_info") or {}).get("has_next_page")
            scrolls = 0
            while has_next and len(items) + len(more) < want_posts and scrolls < 6:
                await page.mouse.wheel(0, 5000)
                await page.wait_for_timeout(2200)
                scrolls += 1
            seen, posts = set(), []
            for it in items + more:
                if it.get("code") and it["code"] not in seen:
                    seen.add(it["code"])
                    posts.append(it)
            out["posts"] = [post_record(n, it) for n, it in enumerate(posts[:want_posts], 1)]

            # Highlights: list from the profile page, stories from each highlight's own page.
            tray = highlight_tray(html)[:max_hl]
            sem = asyncio.Semaphore(parallel)

            async def stories_of(t):
                hid = t["id"].split(":", 1)[1]
                async with sem:
                    pg = await ctx.new_page()
                    try:
                        await pg.goto(f"https://www.instagram.com/stories/highlights/{hid}/",
                                      wait_until="domcontentloaded", timeout=45000)
                        await pg.wait_for_timeout(3000)
                        h = await pg.content()
                        check_page(pg, h)
                    finally:
                        await pg.close()
                conn = embedded(h, REELS_KEY) or {}
                for e in conn.get("edges") or []:
                    if (e.get("node") or {}).get("id") == t["id"]:
                        return e["node"].get("items") or []
                return []

            results = await asyncio.gather(*(stories_of(t) for t in tray), return_exceptions=True)
            for h, (t, its) in enumerate(zip(tray, results), 1):
                if isinstance(its, Stop):
                    raise its
                if isinstance(its, Exception):
                    log("highlight failed", t.get("title"), repr(its)[:80])
                    its = []
                cover = ((t.get("cover_media") or {}).get("cropped_image_version") or {}).get("url", "")
                out["highlights"].append({
                    "n": h, "id": t["id"], "title": t.get("title"), "cover_url": cover,
                    "cover_file": f"media/h{h:02d}_cover.jpg" if cover else "",
                    "stories": [story_record(h, i, it) for i, it in enumerate(its, 1)],
                })
        finally:
            await ctx.close()
    return out


def download(jobs, root):
    def one(job):
        url, rel = job
        dst = root / rel
        if dst.exists() and dst.stat().st_size > 0:
            return True
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.instagram.com/"})
            dst.write_bytes(urllib.request.urlopen(req, timeout=30).read())
            return True
        except Exception as e:
            log("download failed", rel, repr(e)[:80])
            return False
    with ThreadPoolExecutor(16) as ex:
        return sum(ex.map(one, jobs))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("--slug")
    ap.add_argument("--posts", type=int, default=30)
    ap.add_argument("--max-highlights", type=int, default=40)
    a = ap.parse_args()
    handle = a.handle.strip().lstrip("@").split("instagram.com/")[-1].strip("/").split("/")[0].split("?")[0]
    root = client_dir(a.slug or slugify(handle)) / "ig"
    (root / "media").mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    try:
        out = asyncio.run(read(handle, a.posts, a.max_highlights))
    except Stop as e:
        print(str(e))
        sys.exit(3)
    t_ig = time.time() - t0

    jobs = [(out["profile"]["logo_url"], "media/logo.jpg")] if out["profile"].get("logo_url") else []
    for p in out["posts"]:
        jobs += list(zip(p["image_urls"], p["files"]))
    for h in out["highlights"]:
        if h["cover_url"]:
            jobs.append((h["cover_url"], h["cover_file"]))
        jobs += [(s["image_url"], s["file"]) for s in h["stories"] if s["image_url"]]
    ok = download(jobs, root)

    for name in ("profile", "posts", "highlights"):
        (root / f"{name}.json").write_text(json.dumps(out[name], ensure_ascii=False, indent=1), encoding="utf-8")
    pr = out["profile"]
    n_stories = sum(len(h["stories"]) for h in out["highlights"])
    print(f"@{pr['username']} | {pr['full_name']} | {pr['followers']} followers | {pr['category']}")
    print(f"posts: {len(out['posts'])} | highlights: {len(out['highlights'])} ({n_stories} stories) | "
          f"images: {ok}/{len(jobs)} downloaded")
    print(f"time: {t_ig:.1f}s Instagram + {time.time() - t0 - t_ig:.1f}s images = {time.time() - t0:.1f}s")
    print(f"folder: {root}")


if __name__ == "__main__":
    main()
