import threading 
from typing import Dict, Any
from models.exceptions import HardwareError

class PhysicalLockManager:
    """
    مدير الأقفال الفيزيائية (نسخة لايت): يوفر قفل threading.Lock لكل سريال نمبر.
    يضمن عدم حدوث تداخل بين قراءة المونيتور وطلبات المستخدم للتوكن الواحد.
    """
    def __init__(self):
        # بما أننا Single Process، نستخدم قاموس أقفال برمجية بسيطة
        self._physical_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        
    def get_lock(self, serial: str):
        with self._global_lock:
            if serial not in self._physical_locks:
                self._physical_locks[serial] = threading.Lock()
            return self._physical_locks[serial]

    class _LockContext:
        """سياق القفل لضمان التحرير الآمن"""
        def __init__(self, lock: Any, serial: str, timeout: int):
            self.lock = lock
            self.serial = serial
            self.timeout = timeout

        def __enter__(self):
            if not self.lock.acquire(timeout=self.timeout):
                raise HardwareError(f"Token {self.serial} is busy with another task. Please try again.")
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.lock.release()

    def acquire_physical(self, serial: str, timeout: int = 20):
        """الحصول على القفل الفيزيائي لتوكن معين"""
        lock = self.get_lock(serial)
        return self._LockContext(lock, serial, timeout)

    def shutdown(self):
        self._physical_locks.clear()
