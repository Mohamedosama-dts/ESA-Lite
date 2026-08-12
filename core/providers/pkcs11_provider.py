# providers/pkcs11_provider.py
import logging
import os
from typing import List, Optional
from .base_provider import BaseProvider
from .cert_utils import CertUtils
from models.exceptions import HardwareError, AuthError

try:
    import PyKCS11
except ImportError:
    PyKCS11 = None

logger = logging.getLogger("PKCS11Provider")

class PKCS11Provider(BaseProvider):
    """
    مزود الخدمة المعتمد على معيار PKCS#11.
    يعمل كوسيط بين التطبيق ومكتبات الشركات المصنعة (DLLs).
    """
    def __init__(self, dll_path: str):
        self.dll_path = dll_path
        self.pkcs11 = None
        
        # تعزيز المسار لضمان قدرة الويندوز على إيجاد توابع الـ DLL (Dependencies)
        driver_dir = os.path.dirname(self.dll_path)
        if driver_dir and os.path.exists(driver_dir):
            os.environ["PATH"] = driver_dir + os.pathsep + os.environ.get("PATH", "")

        if PyKCS11:
            try:
                self.pkcs11 = PyKCS11.PyKCS11Lib()
                self.pkcs11.load(dll_path)
                info = self.pkcs11.getInfo()
                lib_desc = info.manufacturerID.strip() if info.manufacturerID else "Standard PKCS11"
                logger.info(f"PKCS11 provider initialized: {lib_desc}")
            except Exception as e:
                logger.error(f"Critical: Failed to load PKCS11 DLL: {e}")
                self.pkcs11 = None
        else:
            logger.error("Dependency Missing: PyKCS11 library not found.")

    def is_available(self) -> bool:
        return self.pkcs11 is not None

    def scan_slots(self) -> List[dict]:
        if not self.is_available():
            return []
        tokens = []
        try:
            slots = self.pkcs11.getSlotList(tokenPresent=True)
            for slot_id in slots:
                try:
                    info = self.pkcs11.getTokenInfo(slot_id)
                    
                    # تنظيف النصوص من الـ Null Bytes الناتجة عن تعامل C مع الأوتار
                    label = info.label.replace('\x00', '').strip() if info.label else "Unknown"
                    manufacturer = info.manufacturerID.replace('\x00', '').strip() if info.manufacturerID else "Unknown"
                    serial = info.serialNumber.replace('\x00', '').strip() if info.serialNumber else f"SLOT_{slot_id}"
                    
                    # محاولة استباقية لقراءة بيانات الشهادة لتحسين عرض الواجهة
                    token_type = "E-Signature"
                    cert_info = self._peek_public_cert_info(slot_id)
                    if cert_info:
                        label = cert_info.get('label', label)
                        token_type = cert_info.get('type', token_type)

                    tokens.append({
                        "slot": str(slot_id),
                        "serial": serial,
                        "label": label,
                        "manufacturer": manufacturer,
                        "token_type": token_type,
                        "method": "pkcs11"
                    })
                except Exception as e:
                    logger.debug(f"Skipping slot {slot_id} due to access error: {e}")
                    continue
        except Exception as e:
            logger.error(f"PKCS11 bus scan failed: {e}")
        return tokens

    def _peek_public_cert_info(self, slot_id: int) -> Optional[dict]:
        """استخراج الاسم والنوع بدون الحاجة لـ PIN (القراءة العامة)"""
        session = None
        try:
            session = self.pkcs11.openSession(slot_id, PyKCS11.CKF_SERIAL_SESSION)
            certs = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])
            if certs:
                der_data = bytes(session.getAttributeValue(certs[0], [PyKCS11.CKA_VALUE])[0])
                cert_info = CertUtils.parse_der_certificate(der_data)
                if cert_info:
                    return {"label": cert_info.get('cert_label'), "type": cert_info.get('token_type')}
        except Exception:
            pass
        finally:
            if session:
                try: session.closeSession()
                except: pass
        return None

    def verify_pin(self, slot_id: str, pin: str) -> dict:
        if not self.is_available():
            raise HardwareError("PKCS11 Provider not active.")
            
        session = None
        try:
            slot_int = int(slot_id)
            session = self.pkcs11.openSession(slot_int, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            session.login(pin)
            
            certs = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])
            if not certs:
                raise HardwareError("Authentication succeeded but no certificates found.")
            
            der_data = bytes(session.getAttributeValue(certs[0], [PyKCS11.CKA_VALUE])[0])
            cert_data = CertUtils.parse_der_certificate(der_data)
            
            session.logout()
            session.closeSession()
            return cert_data
            
        except PyKCS11.PyKCS11Error as e:
            err_str = str(e)
            if "CKR_PIN_INCORRECT" in err_str: raise AuthError("INVALID_PIN")
            if "CKR_PIN_LOCKED" in err_str: raise AuthError("PIN_LOCKED")
            raise HardwareError(f"PKCS11 Login Error: {err_str}")
        except Exception as e:
            raise HardwareError(f"Unexpected provider error: {e}")

    def get_certificate_der(self, slot_id: str, pin: Optional[str] = None) -> bytes:
        session = None
        try:
            slot_int = int(slot_id)
            session = self.pkcs11.openSession(slot_int, PyKCS11.CKF_SERIAL_SESSION)
            if pin: session.login(pin)
            
            certs = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])
            if not certs: raise HardwareError("No certificate found.")
            
            der_data = bytes(session.getAttributeValue(certs[0], [PyKCS11.CKA_VALUE])[0])
            if pin: session.logout()
            session.closeSession()
            return der_data
        except Exception as e:
            if session: 
                try: session.closeSession()
                except: pass
            raise HardwareError(f"Failed to retrieve DER: {e}")

    def change_pin(self, slot_id: str, old_pin: str, new_pin: str) -> str:
        try:
            slot_int = int(slot_id)
            session = self.pkcs11.openSession(slot_int, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
            session.login(old_pin)
            session.setPin(old_pin, new_pin)
            session.logout()
            session.closeSession()
            return "PIN changed successfully"
        except Exception as e:
            err_str = str(e)
            if "CKR_PIN_INCORRECT" in err_str: raise AuthError("INVALID_PIN")
            if "CKR_PIN_LOCKED" in err_str: raise AuthError("PIN_LOCKED")
            raise HardwareError(f"Failed to change PIN: {err_str}")