import sys
import os
from pathlib import Path


def _detect_frozen() -> bool:
    """True when running as a packaged binary (Nuitka / PyInstaller), not source."""
    if getattr(sys, "frozen", False):
        return True
    if globals().get("__compiled__") is not None:
        return True
    if bool(getattr(sys, "__nuitka_binary_dir", None)):
        return True
    try:
        prefix = Path(getattr(sys, "prefix", "") or "")
        exe_parent = Path(sys.executable).resolve().parent if sys.executable else Path()
        for candidate in (prefix, exe_parent):
            name = candidate.name.lower()
            if name.startswith("onefile_") or "onefile_" in str(candidate).lower():
                return True
    except Exception:
        pass
    return False


def _appdata_data_dir() -> Path:
    return Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~"))) / "DTS" / "ESA-Lite"


def _is_unsafe_writable(path: Path) -> bool:
    """Refuse onefile extract / temp unpack folders as a writable root."""
    try:
        text = str(path.resolve()).lower()
    except OSError:
        text = str(path).lower()
    return "onefile_" in text


IS_FROZEN = _detect_frozen()

# Writable root is always AppData — never Nuitka onefile extract, never next to the EXE.
DATA_DIR = _appdata_data_dir()
if _is_unsafe_writable(DATA_DIR):
    DATA_DIR = Path(os.path.expanduser("~")) / "AppData" / "Local" / "DTS" / "ESA-Lite"

if IS_FROZEN:
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = Path(sys._MEIPASS)
    else:
        BASE_DIR = Path(sys.executable).parent
        if hasattr(sys, "prefix") and not (BASE_DIR / "assets").exists():
            BASE_DIR = Path(sys.prefix)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Read-only assets (repo or frozen unpack)
ASSETS_DIR = BASE_DIR / "assets"
DRIVERS_DIR = ASSETS_DIR / "drivers"
ASSETS_CONFIG_DIR = ASSETS_DIR / "config"

# 2. Persistent writable data
LOGS_PATH = DATA_DIR / "logs"
CONFIG_DIR = DATA_DIR / "config"
TEMP_DIR = DATA_DIR / "temp"

VENDORS_MAP_PATH = CONFIG_DIR / "vendors_map.json"
STATIC_VENDORS_TEMPLATE = ASSETS_CONFIG_DIR / "vendors_map.json"
USER_SETTINGS = CONFIG_DIR / "user_settings.json"


def cleanup_temp():
    """تنظيف الملفات المؤقتة القديمة للشهادات"""
    try:
        for file in TEMP_DIR.glob("*.cer"):
            file.unlink(missing_ok=True)
    except Exception:
        pass


def ensure_dirs():
    """إنشاء هيكل المجلدات في AppData (Logs / Config / Temp)."""
    for d in [LOGS_PATH, CONFIG_DIR, TEMP_DIR]:
        os.makedirs(str(d), exist_ok=True)


def runtime_paths_report() -> dict:
    """Snapshot used by --print-runtime-paths and startup logs."""
    return {
        "IS_FROZEN": IS_FROZEN,
        "BASE_DIR": str(BASE_DIR),
        "DATA_DIR": str(DATA_DIR),
        "USER_SETTINGS": str(USER_SETTINGS),
        "LOGS_PATH": str(LOGS_PATH),
        "TEMP_DIR": str(TEMP_DIR),
    }


if IS_FROZEN:
    UI_DIST_DIR = BASE_DIR / "interfaces" / "ui" / "dist"
    UI_ASSETS_DIR = UI_DIST_DIR
    ICON_PATH = BASE_DIR / "assets" / "icon.ico"
    LOGO_PATH = UI_DIST_DIR / "assets" / "ESA.png"
    DTS_LOGO = UI_DIST_DIR / "assets" / "dts.png"
else:
    UI_ASSETS_DIR = BASE_DIR / "src" / "assets"
    LOGO_PATH = UI_ASSETS_DIR / "ESA.png"
    ICON_PATH = UI_ASSETS_DIR / "icon.ico"
    DTS_LOGO = UI_ASSETS_DIR / "dts.png"
