import webview
import logging
import os
from pathlib import Path
import pystray
from PIL import Image
from core.containers import ApplicationScope
from models.response_models import OperationResult
from models.exceptions import BaseTokenError
from models.enums import ErrorCode
from .localization import LocaleManager
from config.paths import BASE_DIR, ICON_PATH

logger = logging.getLogger("ESA-Lite-UI")

# المسار الذي ستنتج فيه Vite الملفات النهائية
DIST_DIR = os.path.join(BASE_DIR, "interfaces", "ui", "dist")
INDEX_HTML = os.path.join(DIST_DIR, "index.html")
VITE_DEV_URL = "http://localhost:5173"

class UIBridge:
    """الجسر بين JavaScript وبايثون"""
    def __init__(self, window, engine, inventory, locale, config_loader, config, on_hide_callback=None):
        self._window = window
        self._engine = engine
        self._inventory = inventory
        self._locale = locale
        self._config_loader = config_loader
        self._config = config
        self._on_hide_callback = on_hide_callback
        self._is_closing = False

    def get_tokens(self):
        """جلب قائمة التوكنات للواجهة"""
        if self._is_closing:
            return []
        try:
            # نستخدم المحرك لضمان تحديث المخزن قبل جلب القائمة
            result = self._engine.list_tokens()
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Bridge error in get_tokens: {e}")
            return []

    def login(self, serial, pin):
        try:
            # استدعاء المحرك وتحويل النتيجة لقاموس متوافق مع JSON
            return self._engine.login_token(serial, pin)
        except BaseTokenError as e:
            return OperationResult.failure(message=str(e), error_code=e.code).model_dump(mode='json')
        except Exception as e:
            return OperationResult.failure(message=str(e), error_code=ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def logout(self, serial):
        try:
            return self._engine.logout_token(serial)
        except BaseTokenError as e:
            return OperationResult.failure(message=str(e), error_code=e.code).model_dump(mode='json')
        except Exception as e:
            return OperationResult.failure(message=str(e), error_code=ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def view_cert(self, serial):
        try:
            # معالجة استخراج وفتح ملف الشهادة
            result = self._engine.get_certificate_view_path(serial)
            if result.get("success"):
                path = os.path.normpath(result.get("data"))
                if os.path.exists(path):
                    os.startfile(path)
                    return {"success": True, "message": "Certificate opened"}
            return result
        except Exception as e:
            return {"success": False, "message": f"Failed to open viewer: {e}"}

    def change_pin(self, serial, old_pin, new_pin):
        try:
            return self._engine.change_pin(serial, old_pin, new_pin)
        except Exception as e:
            return OperationResult.failure(message=str(e), error_code=ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def close_app(self, icon=None, triggered_by_window=False):
        """إغلاق التطبيق بالكامل مع إيقاف أيقونة النظام"""
        if self._is_closing:
            return
        self._is_closing = True
        
        logger.info(f"Initiating application shutdown (Triggered by window: {triggered_by_window})...")

        # إيقاف أيقونة التراي أولاً لضمان خروج حلقة الأحداث الخاصة بها
        if self._window and hasattr(self._window, '_tray_icon'):
            try:
                self._window._tray_icon.stop()
            except: pass

        ApplicationScope.shutdown()
        
        # إذا لم يكن الإغلاق ناتجاً عن حدث إغلاق النافذة نفسه، نقوم بتدمير النافذة يدوياً
        if self._window and not triggered_by_window:
            self._window.destroy()

    def hide_to_tray(self, icon=None, item=None):
        """زر مخصص للإرسال للساعة"""
        if self._on_hide_callback:
            self._on_hide_callback()
        elif self._window:
            # Fallback if callback not set
            self._window.hide()
            self._window.on_minimized = lambda: None
        return {"success": True}

    def toggle_language(self):
        try:
            new_lang = self._locale.toggle()
            # حفظ اختيار اللغة الجديد في ملف الإعدادات
            self._config_loader.set_setting("language", new_lang)
            return {"lang": new_lang}
        except Exception as e:
            logger.error(f"Failed to toggle language: {e}")
            return {"lang": "ar"}

    def get_current_translations(self):
        """إرسال اللغة والثيم والهوية للواجهة عند الإقلاع"""
        theme = self._config_loader.get_setting("theme", "light") or "light"
        if theme not in ("light", "dark"):
            theme = "light"
        return {
            "lang": self._locale.lang,
            "theme": theme,
            "version": self._config.AGENT_VERSION,
            "prefix": self._config.AGENT_PREFIX
        }

    def set_theme(self, theme: str):
        value = "dark" if theme == "dark" else "light"
        try:
            self._config_loader.set_setting("theme", value)
            return {"success": True, "theme": value}
        except Exception as e:
            logger.error(f"Failed to set theme: {e}")
            return {"success": False, "theme": value, "message": str(e)}

def start_gui(minimized=False):
    # 1. بدء تشغيل الخدمات الأساسية عند طلب الواجهة (مثل النسخة v1.1.0)
    ApplicationScope.initialize_lite_services()
    # 2. استرجاع المكونات الجاهزة من الـ Container
    inventory = ApplicationScope.get_inventory()
    engine = ApplicationScope.get_engine()
    monitor = ApplicationScope.get_monitor()
    config = ApplicationScope.get_config()
    config_loader = ApplicationScope.get_config_loader()
    locale = LocaleManager(config_loader.get_setting("language", "ar"))

    # إلغاء وضع التطوير والاعتماد كلياً على ملفات الإنتاج النهائية
    # هذا يمنع ظهور نافذة إضافية كانت تظهر بسبب محاولة الاتصال بـ localhost
    url = Path(INDEX_HTML).as_uri()
    logger.info(f"Loading UI from: {url}")

    window = None # تهيئة المتغير للسماح للدوال الداخلية (Closures) بالوصول إليه

    def hide_to_tray(icon=None, item=None):
        """إخفاء النافذة إلى شريط المهام (Tray)"""
        if window:
            window.hide()
            window.on_minimized = lambda: None # منع السلوك الافتراضي عند التصغير

    # إنشاء نسخة من الجسر أولاً لضمان وجود مرجع سليم
    bridge = UIBridge(None, engine, inventory, locale, config_loader, config, on_hide_callback=hide_to_tray)

    window = webview.create_window(
        config.AGENT_FULL_NAME, 
        url=url,
        width=520, height=750,
        resizable=False, frameless=True,
        transparent=False, # العودة للوضع المستقر غير الشفاف
        background_color='#f8fafc', # تعيين خلفية أولية مطابقة للثيم الفاتح
        hidden=True,
        js_api=bridge
    )

    # Update the window reference in the bridge after creation
    bridge._window = window

    # --- System Tray Logic ---
    def show_window(icon, item):
        window.show()
        window.on_minimized = None # Reset minimize handler

    def exit_app_from_tray(icon, item):
        """الخروج من تطبيق التراى"""
        if icon: icon.stop()
        # bridge.close_app handles both shutdown and window destruction
        bridge.close_app()

    def init_tray():
        try:
            # التأكد من المسار المطلق للأيقونة لضمان ظهورها في التراي
            actual_icon_path = str(ICON_PATH.absolute())
            image = Image.open(actual_icon_path) if os.path.exists(actual_icon_path) else Image.new('RGB', (64, 64), color=(212, 175, 55))
        except Exception as e:
            logger.error(f"Tray Icon Error: {e}")
            image = Image.new('RGB', (64, 64), color=(212, 175, 55)) # لون ذهبي احتياطي

        menu = pystray.Menu(
            pystray.MenuItem(locale.get("show"), show_window, default=True),
            pystray.MenuItem(locale.get("hide"), hide_to_tray),
            pystray.MenuItem(locale.get("close"), exit_app_from_tray)
        )
        # تخزين الأيقونة في التطبيق لمنع حذفها من الذاكرة
        window._tray_icon = pystray.Icon("esa_lite", image, config.AGENT_FULL_NAME, menu)
        window._tray_icon.run()

    # تسجيل أحداث الإغلاق
    # نستخدم bridge.close_app لضمان إيقاف التراي والخدمات معاً
    # الـ flag (_is_closing) سيمنع التكرار اللانهائي
    window.events.closing += lambda: bridge.close_app(triggered_by_window=True)
    
    # إظهار النافذة بعد تحميل المحتوى لمنع الوميض الأبيض
    def on_loaded():
        if not minimized:
            window.show()

    window.events.loaded += on_loaded

    # إغلاق وضع التصحيح (debug=False) للإنتاج النهائي
    webview.start(init_tray, debug=False, user_agent='ESA-Lite')
