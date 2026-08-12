import logging
import os
from typing import Optional
from config.paths import TEMP_DIR, cleanup_temp
from core.strategy_manager import StrategyManager
from models.response_models import OperationResult
from models.exceptions import TokenNotFoundError, AuthError, HardwareError, StrategyError, BaseTokenError
from core.utils.physical_lock_manager import PhysicalLockManager
from core.inventory import TokenInventory
from core.providers.cert_utils import CertUtils
from models.enums import ErrorCode

logger = logging.getLogger("CoreEngine")
 
class Engine: # تم تغيير الاسم ليعكس الوظائف المختصرة
    def __init__(self, inventory: TokenInventory, lock_manager: PhysicalLockManager, strategy_manager: StrategyManager):
        self.inventory = inventory
        self.lock_manager = lock_manager
        self.strategy_manager = strategy_manager
        # تنظيف الشهادات القديمة عند بدء تشغيل المحرك
        cleanup_temp()

    def list_tokens(self):
        """قراءة التوكنات المتاحة وتحديث المخزن الحي"""
        raw_tokens = self.strategy_manager.scan_all()
        self.inventory.update(raw_tokens)

        return OperationResult.success_res("Tokens listed", self.inventory.get_all()).model_dump(mode='json')

    def login_token(self, serial: str, pin: str):
        """محاولة تسجيل الدخول وتحديث المخزن"""
        try:
            token_data = self.inventory.get_by_serial(serial, as_object=True)
            if not token_data:
                raise TokenNotFoundError(serial)
                
            slot_id = token_data.slot
            cert_details = self.strategy_manager.verify_pin(
                slot_id, pin, dll_path=token_data.dll_path
            )
            self.inventory.login_success(serial, pin, token_details=cert_details)
            return OperationResult.success_res("Login Successful").model_dump(mode='json')
            
        except BaseTokenError as e:
            return OperationResult.failure(str(e), e.code).model_dump(mode='json')
        except Exception as e:
            logger.error(f"Unexpected Login Error: {e}")
            return OperationResult.failure("Unexpected error occurred", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def logout_token(self, serial: str):
        """تسجيل الخروج (مسح الـ PIN من الذاكرة)"""
        try:
            with self.lock_manager.acquire_physical(serial, timeout=10):
                self.inventory.logout(serial)
                return OperationResult.success_res("Logged out successfully").model_dump(mode='json')
        except BaseTokenError as e:
            return OperationResult.failure(str(e), e.code).model_dump(mode='json')
        except Exception as e:
            return OperationResult.failure(f"Logout failed: {e}", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def change_pin(self, serial: str, old_pin: str, new_pin: str):
        """تغيير الرقم السري للتوكن وتحديثه في الذاكرة إذا كان مسجلاً"""
        try:
            token_data = self.inventory.get_by_serial(serial, as_object=True)
            if not token_data:
                raise TokenNotFoundError(serial)

            with self.lock_manager.acquire_physical(serial, timeout=10):
                self.strategy_manager.change_pin(
                    token_data.slot, old_pin, new_pin, dll_path=token_data.dll_path
                )
                
                self.inventory.logout(serial) 
                return OperationResult.success_res("PIN Updated successfully").model_dump(mode='json')
        except BaseTokenError as e:
            return OperationResult.failure(str(e), e.code).model_dump(mode='json')
        except Exception as e:
            logger.error(f"PIN Change Error for {serial}: {e}")
            return OperationResult.failure("Critical error during PIN change", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def get_token_details(self, serial: str, api_request: bool=False) -> dict:
        """استرجاع بيانات التوكن الموحدة"""
        token = self.inventory.get_by_serial(serial, api_request=api_request)
        if not token: raise TokenNotFoundError(serial)
        return token

    def get_certificate_info(self, serial: str):
        """استخراج بيانات الشهادة بصورة مهيكلة"""
        try:
            token_data = self.inventory.get_by_serial(serial, as_object=True)
            if not token_data: raise TokenNotFoundError(serial)

            # التحقق من وجود الشهادة الخام أو محاولة جلبها من الهاردوير
            if not token_data.certificate_der:
                try:
                    # محاولة القراءة العامة (بدون PIN)
                    der_bytes = self.strategy_manager.get_raw_certificate(
                        token_data.slot, pin=None, dll_path=token_data.dll_path
                    )
                    self.inventory.update_metadata(serial, token_details=CertUtils.parse_der_certificate(der_bytes))
                except Exception:
                    # إذا كانت الشهادة محمية والتوكن غير مسجل دخول
                    if not token_data.logged_in:
                        raise AuthError("Certificate is protected. Please login first.", ErrorCode.SESSION_EXPIRED)
                    
                    # القراءة باستخدام الـ PIN المخزن
                    try:
                        der_bytes = self.strategy_manager.get_raw_certificate(
                            token_data.slot, token_data.pin, dll_path=token_data.dll_path
                        )
                        self.inventory.update_metadata(serial, token_details=CertUtils.parse_der_certificate(der_bytes))
                    except Exception as e:
                        raise StrategyError(f"Hardware failed to provide certificate: {str(e)}")

            data = {
                "subject": token_data.certificate_subject,
                "issuer": token_data.certificate_issuer,
                "expiry": token_data.certificate_expiry,
                "label": token_data.cert_label,
                "der_hex": token_data.certificate_der
            }
            return OperationResult.success_res("Certificate info retrieved", data).model_dump(mode='json')

        except BaseTokenError as e:
            return OperationResult.failure(str(e), e.code).model_dump(mode='json')
        except Exception as e:
            return OperationResult.failure(f"Unexpected error: {e}", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

    def get_certificate_view_path(self, serial: str) -> str:
        """
        تجهيز الشهادة في ملف مؤقت (.cer) ليتمكن الويندوز من عرضها بالبرنامج الافتراضي.
        يماثل سلوك زر "View Certificate" في برنامج EnterSafe.
        """
        res = self.get_certificate_info(serial)
        if not res.get("success"):
            return res # Return the failure result directly
            
        der_hex = res.get("data", {}).get("der_hex")
        
        if not der_hex:
            return OperationResult.failure("Certificate data is unavailable", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')

        temp_cert_path = os.path.join(TEMP_DIR, f"Cert_{serial}.cer")
        
        try:
            with open(temp_cert_path, "wb") as f:
                f.write(bytes.fromhex(der_hex))
            return OperationResult.success_res("Cert file prepared", temp_cert_path).model_dump(mode='json')
        except Exception as e:
            logger.error(f"Failed to create temp cert file: {e}")
            return OperationResult.failure(f"Could not prepare certificate: {e}", ErrorCode.HARDWARE_FAILURE).model_dump(mode='json')
