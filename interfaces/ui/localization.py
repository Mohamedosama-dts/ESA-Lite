import json
import logging
from pathlib import Path
from config.paths import UI_ASSETS_DIR

logger = logging.getLogger("LocaleManager")

class LocaleManager:
    """إدارة نصوص الواجهة والترجمة عبر ملفات JSON"""

    def __init__(self, lang="ar"):
        self.lang = lang
        self.TRANSLATIONS = {}
        self._locales_path = UI_ASSETS_DIR / "locales"
        self._load_all_translations()

    def _load_all_translations(self):
        """تحميل كافة ملفات JSON المتوفرة في مجلد locales"""
        for lang_code in ["ar", "en"]:
            file_path = self._locales_path / f"{lang_code}.json"
            try:
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.TRANSLATIONS[lang_code] = json.load(f)
                else:
                    logger.error(f"Translation file missing: {file_path}")
                    self.TRANSLATIONS[lang_code] = {}
            except Exception as e:
                logger.error(f"Error loading {lang_code} translation: {e}")
                self.TRANSLATIONS[lang_code] = {}

    def get(self, key):
        return self.TRANSLATIONS.get(self.lang, {}).get(key, key)

    def toggle(self):
        self.lang = "en" if self.lang == "ar" else "ar"
        return self.lang