import logging
from typing import List, Optional, Dict
from core.providers.pkcs11_provider import PKCS11Provider
from core.utils.health_check import HealthCheck
from models.exceptions import HardwareError

logger = logging.getLogger("StrategyManager")

class StrategyManager:
    """
    مدير الاستراتيجيات (Lite + multi-DLL):
    يحتفظ بسجل مزودين PKCS#11 — واحد لكل مكتبة قابلة للتحميل.
    لا يوجد مسار توقيع (sign_hash) في هذه النسخة.
    """
    def __init__(self, app_config, config_loader, health_report: Optional[dict] = None):
        self.app_config = app_config
        self.config_loader = config_loader
        self.providers: Dict[str, PKCS11Provider] = {}  # dll_path -> provider
        self.active_provider = None  # first loadable (compat)
        self._initialize(health_report)

    def _initialize(self, health_report: Optional[dict] = None):
        """تجهيز كل المزودين المتاحين بناءً على فحص النظام"""
        report = health_report or HealthCheck(self.config_loader).run_full_check()
        available = list(report.get("available_drivers") or [])
        selected = report.get("selected_driver")
        if selected and selected not in available:
            available.insert(0, selected)

        if not available:
            logger.error("No compatible drivers found. PKCS11 providers cannot be initialized.")
            return

        for dll_path in available:
            try:
                provider = PKCS11Provider(dll_path)
                if provider.is_available():
                    self.providers[dll_path] = provider
                    if self.active_provider is None:
                        self.active_provider = provider
                    logger.info(f"PKCS11 registered: {dll_path}")
                else:
                    logger.warning(f"Provider constructed but unavailable: {dll_path}")
            except Exception as e:
                logger.error(f"Failed to init provider for {dll_path}: {e}")

        if not self.providers:
            logger.error("All PKCS11 provider initializations failed.")

    def _provider_for(self, dll_path: Optional[str] = None) -> PKCS11Provider:
        if dll_path and dll_path in self.providers:
            return self.providers[dll_path]
        if dll_path:
            try:
                provider = PKCS11Provider(dll_path)
                if provider.is_available():
                    self.providers[dll_path] = provider
                    return provider
            except Exception as e:
                raise HardwareError(f"Cannot load PKCS11 DLL at {dll_path}: {e}")
            raise HardwareError(f"PKCS11 provider unavailable for {dll_path}")
        if self.active_provider and self.active_provider.is_available():
            return self.active_provider
        raise HardwareError("No active PKCS11 provider available.")

    def scan_all(self) -> List[dict]:
        """مسح التوكنات من كل المكتبات المتاحة ووسم كل نتيجة بـ dll_path"""
        merged: List[dict] = []
        seen_serials = set()
        for dll_path, provider in self.providers.items():
            if not provider.is_available():
                continue
            try:
                slots = provider.scan_slots()
                for token in slots:
                    token["dll_path"] = dll_path
                    serial = token.get("serial")
                    if serial and serial in seen_serials:
                        logger.debug(f"Skipping duplicate serial {serial} from {dll_path}")
                        continue
                    if serial:
                        seen_serials.add(serial)
                    merged.append(token)
            except Exception as e:
                logger.error(f"PKCS11 scan failed for {dll_path}: {e}")
        return merged

    def get_active_dll_path(self) -> Optional[str]:
        return self.active_provider.dll_path if self.active_provider else None

    def get_available_dll_paths(self) -> List[str]:
        return list(self.providers.keys())

    def verify_pin(self, slot_id: str, pin: str, dll_path: Optional[str] = None) -> dict:
        """التحقق من الـ PIN وجلب بيانات الشهادة"""
        return self._provider_for(dll_path).verify_pin(slot_id, pin)

    def change_pin(self, slot_id: str, old_pin: str, new_pin: str, dll_path: Optional[str] = None) -> str:
        """تغيير الرقم السري عبر المحرك الأصيل"""
        return self._provider_for(dll_path).change_pin(slot_id, old_pin, new_pin)

    def get_raw_certificate(self, slot_id: str, pin: Optional[str] = None, dll_path: Optional[str] = None) -> bytes:
        """استخراج بيانات الشهادة الخام (DER)"""
        return self._provider_for(dll_path).get_certificate_der(slot_id, pin)
