# providers/base_provider.py
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseProvider(ABC):
    """
    العقد الموحد لأي مزود خدمة توقيع.
    يضمن للمحرك أن الدوال ستكون بنفس الاسم ونفس المدخلات والمخرجات دائماً.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """هل هذا المزود جاهز للعمل (المكتبات موجودة)؟"""
        pass

    @abstractmethod
    def scan_slots(self) -> List[dict]:
        """
        مسح المنافذ المتاحة.
        يجب أن تعيد قائمة موحدة من القواميس:
        [{'slot': 1, 'serial': '...', 'label': '...', 'method': 'native/cli'}]
        """
        pass

    @abstractmethod
    def verify_pin(self, slot_id: str, pin: str) -> dict:
        """
        التحقق من صحة الـ PIN.
        يجب أن تعيد قاموس بيانات الشهادة (cert_info) في حالة النجاح.
        يجب أن ترفع AuthError أو HardwareError في حالة الفشل.
        """
        pass

    @abstractmethod
    def get_certificate_der(self, slot_id: str, pin: Optional[str] = None) -> bytes:
        """استخراج الشهادة الخام (DER Bytes). ترفع HardwareError عند الفشل."""
        pass

    @abstractmethod
    def change_pin(self, slot_id: str, old_pin: str, new_pin: str) -> str:
        """تغيير الـ PIN. ترفع AuthError أو HardwareError عند الفشل."""
        pass
