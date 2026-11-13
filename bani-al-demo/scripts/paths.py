"""Where باني الديمو keeps its data and finds the other skills' files.

Data folder: env BANI_DEMO_DATA -> "data_dir" in <skill>/config.json -> ~/bani-al-demo
Settings (local only, never in git): <data>/settings.json. Missing keys fall back to DEFAULTS.

    python paths.py            print the data folder and every resolved setting
    python paths.py --check    exit 1 and list what is missing (WhatsApp number, files, folders)
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
HOME = pathlib.Path.home()


def _skill_cfg():
    cfg = SKILL_DIR / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {}


def data_dir() -> pathlib.Path:
    env = os.environ.get("BANI_DEMO_DATA")
    if env:
        return pathlib.Path(env).expanduser()
    d = _skill_cfg().get("data_dir")
    return pathlib.Path(d).expanduser() if d else HOME / "bani-al-demo"


def _al_bahith_data() -> pathlib.Path:
    """Same lookup as al-bahith's paths.py, so the Excel file and IG session are shared."""
    env = os.environ.get("AL_BAHITH_DATA")
    if env:
        return pathlib.Path(env).expanduser()
    cfg = HOME / ".claude" / "skills" / "al-bahith" / "config.json"
    if cfg.exists():
        try:
            d = json.loads(cfg.read_text(encoding="utf-8-sig")).get("data_dir")
            if d:
                return pathlib.Path(d).expanduser()
        except Exception:
            pass
    return HOME / "al-bahith"


def _clone_kit_scripts() -> str:
    """Newest installed shopify-clone-kit theme-clone scripts folder."""
    pat = str(HOME / ".claude" / "plugins" / "cache" / "shopify-clone-kit" / "shopify-clone-kit" / "*"
              / "skills" / "theme-clone" / "scripts")
    found = glob.glob(pat)

    def ver(p):
        v = pathlib.Path(p).parents[2].name
        return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", v))
    return max(found, key=ver) if found else ""


DATA = data_dir()
AB = _al_bahith_data()
DEFAULTS = {
    "whatsapp": "",               # our number, digits with country code, e.g. 96512345678
    "brand_name": "",             # our name shown on the demo banner
    "banner_text": "ديمو مسوّى لـ {client} — كلمنا نخليه موقعك الحقيقي",
    "wa_message": "هلا، شفت الديمو حق {client}",
    "github_user": "jameellzx",
    "pages_repo": "preview",
    "preview_dir": "C:/dev/preview",
    "templates_dir": str(HOME / "Desktop" / "1st projet" / "قوالب"),
    "katib_dir": str(HOME / "Desktop" / "1st projet" / "katib-clients"),
    "excel": str(AB / "الباحث.xlsx"),
    "ig_state": str(AB / "ig_state"),
    "clone_kit_scripts": "",      # empty = newest installed plugin version
}


def settings() -> dict:
    s = dict(DEFAULTS)
    f = DATA / "settings.json"
    if f.exists():
        s.update({k: v for k, v in json.loads(f.read_text(encoding="utf-8-sig")).items() if v not in (None, "")})
    if not s["clone_kit_scripts"]:
        s["clone_kit_scripts"] = _clone_kit_scripts()
    return s


def save_settings(**kw):
    DATA.mkdir(parents=True, exist_ok=True)
    f = DATA / "settings.json"
    cur = json.loads(f.read_text(encoding="utf-8-sig")) if f.exists() else {}
    cur.update(kw)
    f.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")


def client_dir(slug: str) -> pathlib.Path:
    return DATA / "clients" / slug


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s or "client"


def check() -> list[str]:
    s, missing = settings(), []
    if not re.fullmatch(r"\d{8,15}", s["whatsapp"] or ""):
        missing.append("whatsapp: our WhatsApp number (digits with country code) -> save_settings(whatsapp=...)")
    if not s["brand_name"]:
        missing.append("brand_name: our name for the demo banner")
    for k in ("templates_dir", "excel", "ig_state", "clone_kit_scripts"):
        if not s[k] or not os.path.exists(s[k]):
            missing.append(f"{k}: not found ({s[k] or 'empty'})")
    return missing


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 2 and sys.argv[1] == "--set":
        # python paths.py --set whatsapp=965... brand_name="..."
        save_settings(**dict(a.split("=", 1) for a in sys.argv[2:]))
    print("data:", DATA)
    for k, v in settings().items():
        print(f"  {k}: {v}")
    if "--check" in sys.argv:
        miss = check()
        for m in miss:
            print("MISSING", m)
        sys.exit(1 if miss else 0)
