import ctypes
from ctypes import wintypes
import logging
import threading
import time
from typing import Optional, Callable

logger = logging.getLogger("WindowsMonitor")

# Constants
SCARD_SCOPE_SYSTEM = 2
SCARD_STATE_PRESENT = 0x00000020
SCARD_STATE_CHANGED = 0x00000002
SCARD_STATE_UNAWARE = 0x00000000
INFINITE = 0xFFFFFFFF
SCARD_S_SUCCESS = 0x00000000
SCARD_E_CANCELLED = 0x80100002

SCARDCONTEXT = ctypes.c_void_p # مقبض بحجم مؤشر (64 بت في x64)

class SCARD_READERSTATE(ctypes.Structure):
    _fields_ = [("szReader", wintypes.LPWSTR), ("pvUserData", ctypes.c_void_p),
                ("dwCurrentState", wintypes.DWORD), ("dwEventState", wintypes.DWORD),
                ("cbAtr", wintypes.DWORD), ("rgbAtr", wintypes.BYTE * 36)]

winscard = ctypes.WinDLL('winscard', use_last_error=True)

# تعريف توقيعات WinScard لضمان التوافق مع 64-بت
winscard.SCardEstablishContext.argtypes = [wintypes.DWORD, wintypes.LPCVOID, wintypes.LPCVOID, ctypes.POINTER(SCARDCONTEXT)]
winscard.SCardEstablishContext.restype = wintypes.LONG

winscard.SCardListReadersW.argtypes = [SCARDCONTEXT, wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
winscard.SCardListReadersW.restype = wintypes.LONG

winscard.SCardGetStatusChangeW.argtypes = [SCARDCONTEXT, wintypes.DWORD, ctypes.POINTER(SCARD_READERSTATE), wintypes.DWORD]
winscard.SCardGetStatusChangeW.restype = wintypes.LONG

winscard.SCardReleaseContext.argtypes = [SCARDCONTEXT]
winscard.SCardReleaseContext.restype = wintypes.LONG

winscard.SCardCancel.argtypes = [SCARDCONTEXT]
winscard.SCardCancel.restype = wintypes.LONG

class WindowsMonitor(threading.Thread):
    """
    مراقب أحداث ويندوز (Event-based Monitor):
    استجابة فورية مع استهلاك صفر للمعالج.
    """
    def __init__(self, engine, inventory):
        super().__init__(daemon=True)
        self.engine = engine
        self.inventory = inventory
        self.running = False
        self.hcontext = SCARDCONTEXT(None)
        self.on_change: Optional[Callable] = None
        self.reader_states = []
        self._pnp_reader_name = "\\\\?PnP?\\Notification"

        self._establish_context()

    def _establish_context(self) -> bool:
        try:
            self.hcontext = SCARDCONTEXT(None)
            result = winscard.SCardEstablishContext(SCARD_SCOPE_SYSTEM, None, None, ctypes.byref(self.hcontext))
            if result == SCARD_S_SUCCESS:
                return True
            
            logger.error(f"SCardEstablishContext failed: {hex(result)} (SCardSvr may not be running)")
            return False
        except Exception as e:
            logger.error(f"Error establishing SCard context: {e}")
            return False

    def run(self):
        if not self.hcontext:
            logger.error("WindowsMonitor cannot start: SCard context is null. Fallback to scanner expected.")
            return

        self.running = True
        logger.info("Windows event monitor active")

        try:
            # المسح الأولي
            self._trigger_sync()
            self._update_reader_states(self._get_readers())

            while self.running:
                count = len(self.reader_states)
                states_array = (SCARD_READERSTATE * count)()
                for i in range(count): states_array[i] = self.reader_states[i]
                
                result = winscard.SCardGetStatusChangeW(self.hcontext, INFINITE, states_array, count)

                if result == SCARD_S_SUCCESS:
                    needs_refresh = False
                    for i in range(count):
                        # تحديث الحالة الحالية من الحالة الحدثية لمنع التكرار اللانهائي
                        # نقوم بمسح بت التغيير (CHANGED) لاستخدامه في الطلب القادم
                        self.reader_states[i].dwCurrentState = states_array[i].dwEventState & ~SCARD_STATE_CHANGED
                        
                        if states_array[i].dwEventState & SCARD_STATE_CHANGED:
                            needs_refresh = True
                    
                    if needs_refresh:
                        self._trigger_sync()
                        self._update_reader_states(self._get_readers())
                else:
                    if result == SCARD_E_CANCELLED or not self.running:
                        break
                    logger.warning(f"SCardGetStatusChange failed: {hex(result)}")
                    time.sleep(2) # انتظار في حالة الخطأ
                    
                    if not self._establish_context():
                        logger.error("Recovery failed. Stopping WindowsMonitor.")
                        break

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}")
        finally:
            self._cleanup()

    def _trigger_sync(self):
        """تحديث المخزن (بلاك بوكس)"""
        try:
            # تقليل التأخير لزيادة سرعة الاستجابة اللحظية
            time.sleep(0.3)
            tokens = self.engine.list_tokens()
            # engine.list_tokens() في ESA-Lite يقوم بتحديث Inventory داخلياً
            if self.on_change:
                self.on_change()
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def _update_reader_states(self, readers):
        """
        Updates the list of readers to monitor, preserving the last known state for existing readers.
        """
        old_reader_states = {rs.szReader: rs.dwCurrentState for rs in self.reader_states}
        self.reader_states = []

        # Add PnP reader state
        pnp_reader = SCARD_READERSTATE()
        pnp_reader.szReader = self._pnp_reader_name
        pnp_reader.dwCurrentState = old_reader_states.get(self._pnp_reader_name, SCARD_STATE_UNAWARE)
        self.reader_states.append(pnp_reader)
        
        # Add actual readers
        for reader_name in readers:
            reader_state = SCARD_READERSTATE()
            reader_state.szReader = reader_name
            reader_state.dwCurrentState = old_reader_states.get(reader_name, SCARD_STATE_UNAWARE)
            self.reader_states.append(reader_state)

    def _get_readers(self):
        try:
            pcch = wintypes.DWORD(0)
            if winscard.SCardListReadersW(self.hcontext, None, None, ctypes.byref(pcch)) == SCARD_S_SUCCESS:
                msz = ctypes.create_unicode_buffer(pcch.value)
                if winscard.SCardListReadersW(self.hcontext, None, msz, ctypes.byref(pcch)) == SCARD_S_SUCCESS:
                    return [r for r in msz[:].split('\x00') if r.strip()]
            return []
        except Exception:
            return []

    def stop(self):
        self.running = False
        if self.hcontext:
            winscard.SCardCancel(self.hcontext)

    def _cleanup(self):
        if self.hcontext:
            winscard.SCardReleaseContext(self.hcontext)
            self.hcontext = SCARDCONTEXT(None)