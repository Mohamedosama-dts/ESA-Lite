import json
import os
import uuid
import logging
import shutil
from .paths import VENDORS_MAP_PATH, STATIC_VENDORS_TEMPLATE, USER_SETTINGS

logger = logging.getLogger("ConfigLoader")

_ALLOWED_LANGUAGES = {"ar", "en"}
_ALLOWED_THEMES = {"light", "dark"}


class ConfigLoader:
    """
    مسؤول عن تحميل إعدادات النظام وخرائط التعريفات.
    يدير عملية المزامنة بين قوالب الأصول (Assets) وملفات البيانات الحية (AppData).
    """
    def __init__(self):
        self._vendors_map_file = VENDORS_MAP_PATH
        self._user_settings_file = USER_SETTINGS
        
        self._vendors_config = {}
        self._user_config = {}
        
        self._initialize_configs()

    def _initialize_configs(self):
        """تهيئة كافة الملفات المطلوبة عند التشغيل"""
        self._load_vendors_map_or_sync()
        self._load_user_settings_or_create()

    def _get_defaults(self):
        """
        تعريفات الدرايفرات الافتراضية (Native PKCS#11).

        Policy (asymmetric fallback):
        - ePass / EnterSafe: System32 then assets/drivers/{arch}
        - WatchData (wdpkcs.dll): vendor install path only — NO assets fallback
        """
        return {
            "known_drivers": ["eps2003csp11.dll", "entersafe_p11.dll", "wdpkcs.dll"],
            "no_assets_fallback": ["wdpkcs.dll"],
            "vendor_install_globs": {
                "wdpkcs.dll": [
                    "Watchdata/PROXKey CSP India V3.0/wdpkcs.dll",
                    "Watchdata/*/wdpkcs.dll",
                ]
            },
            "vendor_mapping": {
                "EnterSafe": "eps2003csp11.dll",
                "Feitian": "eps2003csp11.dll",
                "WatchData": "wdpkcs.dll",
                "Watchdata": "wdpkcs.dll",
            }
        }

    def _get_user_defaults(self):
        return {
            "agent_id": str(uuid.uuid4()),
            "language": "ar",
            "theme": "light"
        }

    def _atomic_write_json(self, path, data) -> bool:
        """Write JSON via *.tmp then os.replace. Returns False on disk failure."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception as e:
            logger.error(f"Failed to write JSON to {path}: {e}")
            try:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    def _quarantine_corrupt(self, path):
        try:
            bad = path.with_suffix(path.suffix + ".bad")
            if bad.exists():
                bad.unlink(missing_ok=True)
            path.replace(bad)
            logger.warning(f"Quarantined corrupt config: {bad}")
        except Exception as e:
            logger.error(f"Could not quarantine {path}: {e}")

    def _normalize_user_config(self) -> bool:
        """Fill missing keys and clamp language/theme. Returns True if mutated."""
        updated = False
        defaults = self._get_user_defaults()
        for k, v in defaults.items():
            if k not in self._user_config:
                self._user_config[k] = v
                updated = True

        lang = self._user_config.get("language")
        if lang not in _ALLOWED_LANGUAGES:
            self._user_config["language"] = defaults["language"]
            updated = True

        theme = self._user_config.get("theme")
        if theme not in _ALLOWED_THEMES:
            self._user_config["theme"] = defaults["theme"]
            updated = True

        return updated

    def _load_vendors_map_or_sync(self):
        """تأمين وجود vendors_map عبر النسخ من الأصول أو استخدام الافتراضيات"""
        if not self._vendors_map_file.exists():
            if STATIC_VENDORS_TEMPLATE.exists():
                try:
                    logger.info("Syncing vendors_map from assets to AppData...")
                    self._vendors_map_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(STATIC_VENDORS_TEMPLATE, self._vendors_map_file)
                except Exception as e:
                    logger.error(f"Failed to sync config template: {e}")
            else:
                logger.info("Initializing vendors_map with hardcoded defaults.")
                self._atomic_write_json(self._vendors_map_file, self._get_defaults())

        try:
            with open(self._vendors_map_file, "r", encoding="utf-8") as f:
                self._vendors_config = json.load(f)
        except Exception as e:
            logger.error(f"Corrupt vendors_map.json — resetting defaults: {e}")
            if self._vendors_map_file.exists():
                self._quarantine_corrupt(self._vendors_map_file)
            self._vendors_config = self._get_defaults()
            self._atomic_write_json(self._vendors_map_file, self._vendors_config)
        self._ensure_driver_defaults()

    def _load_user_settings_or_create(self):
        """تحميل ملف user_settings.json ومطابقته مع القالب الافتراضي"""
        if not self._user_settings_file.exists():
            self._user_config = self._get_user_defaults()
            if not self._save_user_settings():
                logger.error("Could not create user_settings.json under AppData")
            return

        try:
            with open(self._user_settings_file, "r", encoding="utf-8") as f:
                self._user_config = json.load(f)
            if not isinstance(self._user_config, dict):
                raise ValueError("user_settings.json root is not an object")
            if self._normalize_user_config():
                self._save_user_settings()
        except Exception as e:
            logger.error(f"Corrupt user_settings.json — resetting defaults: {e}")
            if self._user_settings_file.exists():
                self._quarantine_corrupt(self._user_settings_file)
            self._user_config = self._get_user_defaults()
            self._save_user_settings()

    def _save_json(self, path, data):
        return self._atomic_write_json(path, data)

    def _save_user_settings(self) -> bool:
        return self._atomic_write_json(self._user_settings_file, self._user_config)

    def get_setting(self, key: str, default=None):
        return self._user_config.get(key, default)

    def set_setting(self, key: str, value) -> bool:
        if key == "language" and value not in _ALLOWED_LANGUAGES:
            raise ValueError(f"Invalid language: {value}")
        if key == "theme" and value not in _ALLOWED_THEMES:
            raise ValueError(f"Invalid theme: {value}")
        self._user_config[key] = value
        if not self._save_user_settings():
            raise OSError(f"Failed to persist setting '{key}' to {self._user_settings_file}")
        return True

    def _ensure_driver_defaults(self):
        """Merge newly added driver policy keys into an existing vendors_map."""
        defaults = self._get_defaults()
        changed = False

        existing = self._vendors_config.get("known_drivers") or []
        existing_lower = {d.lower() for d in existing}
        for dll in defaults["known_drivers"]:
            if dll.lower() not in existing_lower:
                existing.append(dll)
                existing_lower.add(dll.lower())
                changed = True
        self._vendors_config["known_drivers"] = existing

        if "no_assets_fallback" not in self._vendors_config:
            self._vendors_config["no_assets_fallback"] = list(defaults["no_assets_fallback"])
            changed = True

        globs = self._vendors_config.setdefault("vendor_install_globs", {})
        for dll, patterns in defaults["vendor_install_globs"].items():
            if dll not in globs:
                globs[dll] = list(patterns)
                changed = True

        mapping = self._vendors_config.setdefault("vendor_mapping", {})
        for key, dll_name in defaults["vendor_mapping"].items():
            if key not in mapping:
                mapping[key] = dll_name
                changed = True

        if changed:
            self._atomic_write_json(self._vendors_map_file, self._vendors_config)

    def get_scan_list(self):
        """قائمة الـ DLLs المطلوبة للفحص"""
        return self._vendors_config.get("known_drivers", [])

    def allows_assets_fallback(self, dll_name: str) -> bool:
        """ePass-style middleware may use assets; WatchData may not."""
        blocked = {d.lower() for d in self._vendors_config.get("no_assets_fallback", [])}
        return dll_name.lower() not in blocked

    def get_vendor_install_globs(self, dll_name: str):
        """Relative System32 globs for install-only DLLs (e.g. WatchData PROXKey)."""
        return self._vendors_config.get("vendor_install_globs", {}).get(dll_name, [])

    def resolve_driver(self, manufacturer_str: str):
        """ربط اسم المصنع بملف الدرايفر المناسب"""
        if not manufacturer_str:
            return None
        mapping = self._vendors_config.get("vendor_mapping", {})
        for key, dll_name in mapping.items():
            if key.lower() in manufacturer_str.lower():
                return dll_name
        return None
