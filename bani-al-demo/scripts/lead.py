"""Find one client in الباحث.xlsx («عملائي», then «وسط») and start its folder.

    python lead.py "<name or instagram handle or link>"      -> clients/<slug>/lead.json, prints slug
    python lead.py --list                                     -> every client row (number, name, IG, field)

Prints MATCHES when more than one row fits (Claude asks the user which), NOT_FOUND when none.
"""
from __future__ import annotations

import json
import re
import sys

import openpyxl

from paths import client_dir, settings, slugify

SHEETS = ("عملائي", "وسط")


def handle_of(url):
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", str(url or ""))
    return m.group(1).lower() if m else ""


def rows():
    wb = openpyxl.load_workbook(settings()["excel"], read_only=True, data_only=True)
    for sheet in SHEETS:
        if sheet not in wb.sheetnames:
            continue
        it = wb[sheet].iter_rows(values_only=True)
        head = [str(h or "") for h in next(it, [])]
        for i, r in enumerate(it, start=2):
            d = {h: v for h, v in zip(head, r) if h}
            if not any(d.values()):
                continue
            d["_sheet"], d["_row"] = sheet, i
            d["_handle"] = handle_of(d.get("رابط انستقرام"))
            yield d


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    all_rows = list(rows())
    if sys.argv[1] == "--list":
        for n, d in enumerate(all_rows, 1):
            print(f"{n}. {d.get('الاسم')} | @{d['_handle']} | {d.get('المجال') or ''} | "
                  f"{d.get('عدد المتابعين') or ''} followers | {d['_sheet']}"
                  + (f" | demo: {d.get('الموقع التجريبي') or d.get('رابط الديمو')}"
                     if d.get("الموقع التجريبي") or d.get("رابط الديمو") else ""))
        return
    q = sys.argv[1].strip()
    qh = handle_of(q) or q.lstrip("@").lower()
    hits = [d for d in all_rows if d["_handle"] and d["_handle"] == qh]
    if not hits:
        hits = [d for d in all_rows if q.lower() in str(d.get("الاسم") or "").lower()]
    if not hits:
        print("NOT_FOUND"); sys.exit(2)
    if len(hits) > 1:
        print("MATCHES")
        for d in hits:
            print(f"  {d.get('الاسم')} | @{d['_handle']} | {d['_sheet']} row {d['_row']}")
        sys.exit(3)
    d = hits[0]
    slug = slugify(d["_handle"] or d.get("الاسم"))
    out = client_dir(slug)
    out.mkdir(parents=True, exist_ok=True)
    lead = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items()}
    lead["slug"] = slug
    (out / "lead.json").write_text(json.dumps(lead, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"slug: {slug}")
    print(f"name: {d.get('الاسم')} | @{d['_handle']} | field: {d.get('المجال')} | sheet {d['_sheet']} row {d['_row']}")
    print(f"folder: {out}")


if __name__ == "__main__":
    main()
