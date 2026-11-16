"""Publish an approved demo to GitHub Pages and record the link. Run ONLY after the user said OK to the screenshots.

    python publish.py <slug>            publish (or update) the demo
    python publish.py <slug> --test     publish with the test WhatsApp number, for the user to look at only:
                                        nothing is written to the Excel file or demos.md; publish again
                                        without --test after the real number is set (same link)
    python publish.py --setup           first time only: create the public Pages repo (also done automatically)

- Repo: github.com/<github_user>/<pages_repo> (public), local clone <preview_dir>. robots.txt blocks crawlers,
  the root index.html is empty (no list of clients), every demo page has a noindex meta.
- Each client gets one folder <slug>-<6 random letters>; publishing the same client again updates that folder,
  so the link stays the same.
- Then: waits until the live link answers 200, writes «الموقع التجريبي» and «تاريخ الديمو» on the client's row
  in الباحث.xlsx, and appends the link to <data>/demos.md (local only).
Status words: NOT_CHECKED (check.py has not passed), EXCEL_LOCKED (close the Excel file and run again; the page
is already live), NOT_LIVE_YET (GitHub Pages still building; link printed anyway).
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import random
import shutil
import string
import subprocess
import sys
import time
import urllib.request

from paths import DATA, client_dir, settings

ROBOTS = "User-agent: *\nDisallow: /\n"
ROOT_INDEX = ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">'
              '<title></title></head><body></body></html>\n')


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r


def setup(s):
    user, repo, local = s["github_user"], s["pages_repo"], pathlib.Path(s["preview_dir"])
    exists = run(["gh", "repo", "view", f"{user}/{repo}"], check=False).returncode == 0
    if not exists:
        run(["gh", "repo", "create", f"{user}/{repo}", "--public",
             "--description", "Website previews (not indexed)"])
        print(f"created repo {user}/{repo}")
    if not (local / ".git").exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        if exists:
            run(["gh", "repo", "clone", f"{user}/{repo}", str(local)])
        else:
            local.mkdir(parents=True, exist_ok=True)
            run(["git", "init", "-b", "main"], cwd=local)
            run(["git", "remote", "add", "origin", f"https://github.com/{user}/{repo}.git"], cwd=local)
    for name, text in (("robots.txt", ROBOTS), ("index.html", ROOT_INDEX), (".nojekyll", "")):
        p = local / name
        if not p.exists():
            p.write_text(text, encoding="utf-8")
    run(["git", "add", "-A"], cwd=local)
    if run(["git", "status", "--porcelain"], cwd=local).stdout.strip():
        run(["git", "commit", "-m", "Set up previews (robots blocked, no index)"], cwd=local)
        run(["git", "push", "-u", "origin", "main"], cwd=local)
    pages = run(["gh", "api", f"repos/{user}/{repo}/pages"], check=False)
    if pages.returncode != 0:
        run(["gh", "api", "-X", "POST", f"repos/{user}/{repo}/pages",
             "-f", "source[branch]=main", "-f", "source[path]=/"])
        print("GitHub Pages turned on")
    return local


def folder_for(slug, local):
    for d in local.iterdir():
        if d.is_dir() and d.name.startswith(slug + "-") and len(d.name) == len(slug) + 7:
            return d.name
    return f"{slug}-" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))


def record_excel(s, lead, link, today):
    import openpyxl
    path = s["excel"]
    try:
        wb = openpyxl.load_workbook(path)
    except PermissionError:
        return "EXCEL_LOCKED"
    ws = wb[lead["_sheet"]]
    head = [c.value for c in ws[1]]
    cols = {}
    if "رابط الديمو" in head and "الموقع التجريبي" not in head:  # old column name -> the one al-bahith uses
        ws.cell(row=1, column=head.index("رابط الديمو") + 1, value="الموقع التجريبي")
        head[head.index("رابط الديمو")] = "الموقع التجريبي"
    for name in ("الموقع التجريبي", "تاريخ الديمو"):
        if name not in head:
            ws.cell(row=1, column=len(head) + 1, value=name)
            head.append(name)
        cols[name] = head.index(name) + 1
    # Find the row again by Instagram link (rows may have moved since lead.py ran).
    ig_col = head.index("رابط انستقرام") + 1 if "رابط انستقرام" in head else None
    row = lead["_row"]
    if ig_col and lead.get("_handle"):
        for r in range(2, ws.max_row + 1):
            v = str(ws.cell(row=r, column=ig_col).value or "").lower()
            if f"instagram.com/{lead['_handle']}" in v:
                row = r
                break
    ws.cell(row=row, column=cols["الموقع التجريبي"], value=link).hyperlink = link
    ws.cell(row=row, column=cols["تاريخ الديمو"], value=today)
    try:
        wb.save(path)
    except PermissionError:
        return "EXCEL_LOCKED"
    return "OK"


def pages_built(s, tries=40):
    """Wait for the GitHub Pages build of the last push. Many pushes in a row can leave the latest build
    "errored" while the old page still answers 200 (seen 2026-11-16): then ask GitHub to build again, once."""
    api = f"repos/{s['github_user']}/{s['pages_repo']}/pages/builds"
    retried = False
    time.sleep(15)  # let GitHub register the new push first
    for _ in range(tries):
        st = run(["gh", "api", f"{api}/latest", "--jq", ".status"], check=False).stdout.strip()
        if st == "built":
            return True
        if st == "errored" and not retried:
            run(["gh", "api", "-X", "POST", api], check=False)
            retried = True
        time.sleep(10)
    print("PAGES_BUILD_PENDING: GitHub Pages has not finished building; check the link again in a few minutes")
    return False


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    s = settings()
    if sys.argv[1:] == ["--setup"]:
        setup(s)
        return
    slug = sys.argv[1]
    test = "--test" in sys.argv[2:]
    if not test and (s["whatsapp"].endswith("000000") or s["brand_name"].strip().upper() == "TEST"):
        print("TEST_NUMBER: set our real WhatsApp + brand name (paths.py --set ...), rebuild, check, then publish")
        sys.exit(2)
    cdir = client_dir(slug)
    chk = cdir / "check.json"
    site = cdir / "site" / "index.html"
    if not chk.exists() or not json.loads(chk.read_text(encoding="utf-8")).get("pass") \
            or chk.stat().st_mtime < site.stat().st_mtime:
        print("NOT_CHECKED: run check.py after the last build, and get the user's OK first")
        sys.exit(2)

    local = setup(s)
    folder = folder_for(slug, local)
    dst = local / folder
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(cdir / "site", dst)
    run(["git", "add", "-A"], cwd=local)
    if run(["git", "status", "--porcelain"], cwd=local).stdout.strip():
        run(["git", "commit", "-m", f"Preview {folder}"], cwd=local)
        run(["git", "push", "origin", "main"], cwd=local)

    link = f"https://{s['github_user']}.github.io/{s['pages_repo']}/{folder}/"
    pages_built(s)
    live = False
    for _ in range(36):  # up to ~6 minutes for the Pages build
        try:
            if urllib.request.urlopen(link, timeout=15).status == 200:
                live = True
                break
        except Exception:
            pass
        time.sleep(10)

    today = datetime.date.today().isoformat()
    if test:
        print(f"link: {link}")
        print("live" if live else "NOT_LIVE_YET")
        print("TEST publish: not recorded in Excel or demos.md")
        return
    lead = json.loads((cdir / "lead.json").read_text(encoding="utf-8"))
    xl = record_excel(s, lead, link, today)
    demos = DATA / "demos.md"
    if not demos.exists():
        demos.write_text("# Demos\n\n| date | client | link |\n|---|---|---|\n", encoding="utf-8")
    text = demos.read_text(encoding="utf-8")
    line = f"| {today} | {lead.get('الاسم')} (@{lead.get('_handle')}) | {link} |\n"
    if link not in text:
        demos.write_text(text + line, encoding="utf-8")
    (cdir / "published.json").write_text(json.dumps({"link": link, "date": today, "folder": folder},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"link: {link}")
    print("live" if live else "NOT_LIVE_YET")
    print("excel:", xl)


if __name__ == "__main__":
    main()
