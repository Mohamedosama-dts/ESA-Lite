import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger("DefenderHint")

# Constants for Windows Event Log
EVENTLOG_INFORMATION_TYPE = 0x0004

advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

def register_with_event_log():
    """
    تسجيل حدث في Windows Event Log عند بدء التشغيل.
    هذا الإجراء يزيد من شفافية التطبيق ويقلل من نقاط الاشتباه (Suspicion Score).
    """
    try:
        # تعريف التوقيعات لضمان التوافق مع x64
        advapi32.RegisterEventSourceW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        advapi32.RegisterEventSourceW.restype = wintypes.HANDLE

        advapi32.ReportEventW.argtypes = [
            wintypes.HANDLE, wintypes.WORD, wintypes.WORD, wintypes.DWORD,
            wintypes.PSID, wintypes.WORD, wintypes.DWORD,
            ctypes.POINTER(wintypes.LPCWSTR), ctypes.c_void_p
        ]
        advapi32.ReportEventW.restype = wintypes.BOOL

        advapi32.DeregisterEventSource.argtypes = [wintypes.HANDLE]
        advapi32.DeregisterEventSource.restype = wintypes.BOOL

        h_event_log = advapi32.RegisterEventSourceW(None, "ESA-Lite")
        if not h_event_log:
            return

        message = "ESA-Lite started. Native USB token monitoring active."
        strings = (wintypes.LPCWSTR * 1)(message)
        
        # Event ID 100: تطبيق بدأ بنجاح
        advapi32.ReportEventW(h_event_log, EVENTLOG_INFORMATION_TYPE, 0, 100, None, 1, 0, strings, None)
        advapi32.DeregisterEventSource(h_event_log)
        logger.debug("Successfully signaled startup event to Windows Event Log.")
    except Exception as e:
        logger.debug(f"Event Log signaling skipped: {e}")