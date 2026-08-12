import threading
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime
from pydantic import ValidationError
from models.token_model import TokenData, ScanMethod, TokenType
from core.utils.win_cert_store import WinCertStore

logger = logging.getLogger("Inventory")

class TokenInventory:
    """
    المخزن الحي (In-Memory Store) لحالة التوكنات.
    يحتفظ بآخر حالة معروفة للتوكنات لخدمة الـ API بسرعة (Caching).
    """
    def __init__(self):
        self._tokens: Dict[str, TokenData] = {} # Key: Serial, Value: TokenData Object
        self._data_lock = threading.RLock() # قفل لحماية البيانات أثناء القراءة/الكتابة

    def update(self, detected_tokens: List[Dict]) -> List[TokenData]:
        """
        تحديث ذكي (Inventory Sync):
        يحافظ على حالة تسجيل الدخول (PIN) طالما التوكن متصل.
        """
        new_tokens_list = []
        with self._data_lock:
            current_serials = set()
            
            for token in detected_tokens:
                serial = token.get('serial')
                if not serial: continue # حماية من البيانات المشوهة
                
                current_serials.add(serial)
                
                # إذا كان التوكن موجوداً مسبقاً، نحدث بياناته الفيزيائية (Slot) فقط
                if serial in self._tokens:
                    entry = self._tokens[serial]
                    entry.slot = token['slot']
                    entry.last_connected_at = datetime.now()
                    if token.get('dll_path'):
                        entry.dll_path = token['dll_path']
                    
                    # تحديث الحقول مع ضمان توافق الأنواع (Enum Conversion)
                    if token.get('label'): entry.label = token['label']
                    if token.get('method'): 
                        entry.method = ScanMethod(token['method'])
                    if token.get('token_type'): 
                        entry.token_type = TokenType(token['token_type'])
                    if token.get('manufacturer'):
                        entry.manufacturer = token['manufacturer']
                    if token.get('model'):
                        entry.model = token['model']
                else:
                    # توكن جديد كلياً
                    try:
                        # إنشاء كائن TokenData مباشرة من القاموس القادم من البروفايدر
                        token_obj = TokenData.model_validate({
                            "slot": token['slot'],
                            "method": ScanMethod(token.get('method', 'pkcs11')),
                            "serial": serial,
                            "label": token.get('label', 'Unknown'),
                            "manufacturer": token.get('manufacturer', 'Unknown'),
                            "model": token.get('model', 'Unknown'),
                            "token_type": TokenType(token.get('token_type', 'E-Signature')),
                            "dll_path": token.get('dll_path'),
                        })
                        self._tokens[serial] = token_obj
                        new_tokens_list.append(token_obj)
                        logger.debug(f"New token: {serial} [{token_obj.label}] dll={token_obj.dll_path}")
                    except ValidationError as e:
                        logger.error(f"Failed to register token {serial}: {e}")

            # تنظيف المفقود (Disconnection Phase)
            for serial in list(self._tokens.keys()):
                if serial not in current_serials:
                    # الحصول على بيانات التوكن قبل الحذف للقيام بعملية تنظيف مخزن ويندوز
                    token_data = self._tokens[serial]
                    
                    # إذا كانت الشهادة منشورة (Subject Name متوفر)، نقوم بحذفها
                    if token_data.certificate_subject:
                        logger.debug(f"Token {serial} disconnect: removing public cert from Windows MY store")
                        WinCertStore.remove_certificate(token_data.certificate_subject)
                    else:
                        logger.debug(f"Skipping certificate removal for {serial}: No subject found in metadata.")

                    logger.warning(f"Token disconnected: {serial}")
                    del self._tokens[serial]

        return new_tokens_list

    def login_success(self, serial: str, pin: str, token_details: Dict = None):
        """تسجيل نجاح الدخول وحفظ الـ PIN والبيانات التفصيلية"""
        with self._data_lock:
            if serial in self._tokens:
                if token_details:
                    self.update_metadata(serial, token_details)

                # الكائن قد يُستبدل داخل update_metadata
                token = self._tokens[serial]
                token.logged_in = True
                token.pin = pin

                logger.info(f"Token {serial} logged in")

                if token.certificate_der:
                    try:
                        WinCertStore.publish_certificate(bytes.fromhex(token.certificate_der))
                    except Exception as e:
                        logger.warning(f"Failed to publish certificate for {serial} (non-fatal): {e}")
                else:
                    logger.debug(f"Skip WinCert publish for {serial}: no certificate_der after login")

    def update_metadata(self, serial: str, token_details: Dict):
        """تحديث بيانات الشهادة والتوكن دون تغيير حالة المصادقة"""
        with self._data_lock:
            if serial not in self._tokens: return
            
            token = self._tokens[serial]
            
            # توحيد مسميات الحقول لضمان مطابقتها لموديل Pydantic (Mapping normalization)
            mapping = {
                'subject': 'certificate_subject',
                'issuer': 'certificate_issuer',
                'expiry': 'certificate_expiry'
            }
            for src_key, target_key in mapping.items():
                if src_key in token_details and target_key not in token_details:
                    token_details[target_key] = token_details[src_key]

            # معالجة مشكلة التوقيت الزائد (ISO format cleanup)
            expiry = token_details.get('certificate_expiry')
            if isinstance(expiry, str) and expiry.endswith('Z') and '+' in expiry:
                token_details['certificate_expiry'] = expiry.replace('Z', '')

            # دمج البيانات وإعادة التحقق عبر Pydantic
            current_data = token.model_dump()
            
            # استعادة الحقول المحمية التي تم استبعادها من الـ dump
            # لضمان عدم ضياعها أثناء إعادة بناء الكائن
            if token.pin: 
                current_data['pin'] = token.pin
            if token.certificate_der:
                current_data['certificate_der'] = token.certificate_der

            current_data.update(token_details)
            try:
                self._tokens[serial] = TokenData.model_validate(current_data)
            except ValidationError as e:
                logger.error(f"Failed to update token metadata for {serial}: {e}")
                
    def logout(self, serial: str):
        """تسجيل الخروج ومسح الـ PIN وإزالة الشهادة العامة من مخزن ويندوز"""
        with self._data_lock:
            if serial in self._tokens:
                token = self._tokens[serial]
                subject = token.certificate_subject
                token.logged_in = False
                token.pin = None
                token.certificate_der = None
                token.certificate_public_key = None
                logger.info(f"Token {serial} logged out")
                if subject:
                    try:
                        WinCertStore.remove_certificate(subject)
                    except Exception as e:
                        logger.warning(f"Failed to remove certificate for {serial} on logout (non-fatal): {e}")

    def get_all(self) -> List[Dict]:
        """
        إرجاع قائمة التوكنات كقواميس (Safe Dump).
        ملاحظة: الـ PIN سيتم استبعاده تلقائياً بفضل Field(exclude=True) في الموديل.
        """
        with self._data_lock:
            return [t.model_dump(mode='json') for t in self._tokens.values()]

    def get_by_serial(self, serial: str, as_object: bool = False, api_request: bool = False) -> Optional[Union[Dict, TokenData]]:
        """البحث عن توكن معين وإرجاعه ككائن أو قاموس"""
        with self._data_lock:
            token = self._tokens.get(serial)
            if token:
                if as_object:
                    return token
                if api_request:
                    return token.model_dump(mode='json') # Excludes PIN & DER

                return token.model_dump(mode='json') 
            return None

    def is_empty(self) -> bool:
        with self._data_lock:
            return len(self._tokens) == 0