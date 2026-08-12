import os
import ctypes
import sys
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple
from config.paths import BASE_DIR, DRIVERS_DIR
from ctypes import wintypes
from models.enums import ErrorCode

if TYPE_CHECKING:
    from config.config_loader import ConfigLoader

# Win32 Service Control Manager Constants
WIN32_CONST = {
    "SC_MANAGER_CONNECT": 0x0001,
    "SERVICE_QUERY_STATUS": 0x0004,
    "SERVICE_START": 0x0010,
    "SERVICE_RUNNING": 0x00000004,
    "SERVICE_START_PENDING": 0x00000002
}
SC_HANDLE = ctypes.c_void_p  # استخدام c_void_p يضمن سعة 64-بت للمقابض في x64

logger = logging.getLogger("HealthCheck")

class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", wintypes.DWORD), ("dwCurrentState", wintypes.DWORD),
        ("dwControlsAccepted", wintypes.DWORD), ("dwWin32ExitCode", wintypes.DWORD),
        ("dwServiceSpecificExitCode", wintypes.DWORD), ("dwCheckPoint", wintypes.DWORD),
        ("dwWaitHint", wintypes.DWORD)
    ]

class HealthCheck:
    def __init__(self, config_loader: 'ConfigLoader'):
        # استخدام المسار الأساسي الموحد من config.paths
        self.config_loader = config_loader
        self.base_dir = Path(BASE_DIR)
        # نعتمد على معمارية بايثون نفسها لضمان توافق الـ ctypes
        is_64bits = sys.maxsize > 2**32
        self.arch = "x64" if is_64bits else "x86"
        self.strategy = {
            "status": "UNKNOWN",
            "selected_driver": None,       # first loadable (compat)
            "available_drivers": [],       # all loadable abs paths (multi-DLL)
            "drivers_found": {},
            "is_smart_card_service_running": False,
            "recommended_monitor": "windows_event", # الافتراضي هو الأضمن
            "issues": [],
            "error_codes": []
        }

    def run_full_check(self):
        """نقطة الدخول الرئيسية للفحص"""
        logger.info(f"Starting system scan [arch: {self.arch}]...")

        self._check_smart_card_service_status()
        self._check_drivers()

        if not self.strategy["available_drivers"]:
            self.strategy["status"] = "CRITICAL"
            self.strategy["error_codes"].append(ErrorCode.DLL_NOT_FOUND)
            self.strategy["issues"].append("No valid PKCS11 driver found.")
        elif not self.strategy["is_smart_card_service_running"]:
            self.strategy["status"] = "WARNING"
            self.strategy["error_codes"].append(ErrorCode.SMARTCARD_SERVICE_STOPPED)
            self.strategy["issues"].append("Smart Card service is not running.")
        else:
            self.strategy["status"] = "HEALTHY"

        if self.strategy["is_smart_card_service_running"]:
            self.strategy["recommended_monitor"] = "windows_event"

        return self.strategy

    def _check_smart_card_service_status(self):
        """التحقق من حالة خدمة SCardSvr ومحاولة تشغيلها آلياً إذا كانت متوقفة"""
        try:
            advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
            
            advapi32.OpenSCManagerW.restype = SC_HANDLE
            advapi32.OpenSCManagerW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            
            advapi32.OpenServiceW.restype = SC_HANDLE
            advapi32.OpenServiceW.argtypes = [SC_HANDLE, wintypes.LPCWSTR, wintypes.DWORD]
            
            advapi32.QueryServiceStatus.restype = wintypes.BOOL
            advapi32.QueryServiceStatus.argtypes = [SC_HANDLE, ctypes.POINTER(SERVICE_STATUS)]
            
            advapi32.StartServiceW.restype = wintypes.BOOL
            advapi32.StartServiceW.argtypes = [SC_HANDLE, wintypes.DWORD, ctypes.c_void_p]
            
            advapi32.CloseServiceHandle.restype = wintypes.BOOL
            advapi32.CloseServiceHandle.argtypes = [SC_HANDLE]

            scm = advapi32.OpenSCManagerW(None, None, WIN32_CONST["SC_MANAGER_CONNECT"])
            if not scm:
                logger.warning(f"SC Manager access failed: {ctypes.get_last_error()}")
                return

            service_access = WIN32_CONST["SERVICE_QUERY_STATUS"] | WIN32_CONST["SERVICE_START"]
            service = advapi32.OpenServiceW(scm, "SCardSvr", service_access)
            
            if not service:
                service = advapi32.OpenServiceW(scm, "SCardSvr", WIN32_CONST["SERVICE_QUERY_STATUS"])

            if service:
                status = SERVICE_STATUS()
                if advapi32.QueryServiceStatus(service, ctypes.byref(status)):
                    if status.dwCurrentState in [WIN32_CONST["SERVICE_RUNNING"], WIN32_CONST["SERVICE_START_PENDING"]]:
                        self.strategy["is_smart_card_service_running"] = True
                    else:
                        logger.info("SCardSvr is stopped. Attempting auto-start...")
                        if advapi32.StartServiceW(service, 0, None):
                            for _ in range(5):
                                time.sleep(1)
                                advapi32.QueryServiceStatus(service, ctypes.byref(status))
                                if status.dwCurrentState in [WIN32_CONST["SERVICE_RUNNING"], WIN32_CONST["SERVICE_START_PENDING"]]:
                                    self.strategy["is_smart_card_service_running"] = True
                                    logger.info("Smart Card service started.")
                                    break
                        else:
                            logger.warning(f"SCardSvr start failed: {ctypes.get_last_error()}")
                
                advapi32.CloseServiceHandle(service)
            advapi32.CloseServiceHandle(scm)

            if self.strategy["is_smart_card_service_running"]:
                logger.info("Smart Card service is active.")
            else:
                logger.warning("Smart Card service (SCardSvr) is not running. Event monitor will fail.")

        except Exception as e:
            logger.error(f"Error checking service status: {e}")

    def _resolve_candidate_paths(self, dll: str, system32: Path, assets_drivers: Path) -> List[Tuple[Path, str]]:
        """
        Build ordered (path, source) candidates for one DLL name.
        WatchData: vendor install paths only (no assets).
        ePass-family: System32 root, then assets fallback.
        """
        candidates: List[Tuple[Path, str]] = []
        seen = set()

        def _add(path: Path, source: str):
            try:
                key = str(path.resolve()) if path.exists() else str(path)
            except OSError:
                key = str(path)
            if key in seen:
                return
            if path.exists():
                seen.add(key)
                candidates.append((path, source))

        # Install-only vendor globs (WatchData PROXKey, etc.)
        for rel in self.config_loader.get_vendor_install_globs(dll):
            pattern = str(system32 / rel)
            if "*" in rel or "?" in rel:
                for match in system32.glob(rel):
                    if match.is_file():
                        _add(match, "VENDOR_INSTALL")
            else:
                _add(Path(pattern), "VENDOR_INSTALL")

        # Flat System32\{dll}
        _add(system32 / dll, "SYSTEM")

        # Assets fallback — asymmetric policy (ePass yes, WatchData no)
        if self.config_loader.allows_assets_fallback(dll):
            _add(assets_drivers / dll, "ASSETS_DRIVER")

        return candidates

    def _check_drivers(self):
            # Multi-DLL: probe every known driver; collect all loadable paths
            target_dlls = self.config_loader.get_scan_list()
            system32 = Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32'
            assets_drivers = DRIVERS_DIR / self.arch
            available: List[str] = []
            watchdata_requested = any(d.lower() == "wdpkcs.dll" for d in target_dlls)
            watchdata_found = False

            for dll in target_dlls:
                candidates = self._resolve_candidate_paths(dll, system32, assets_drivers)
                dll_entry = {
                    "candidates": [],
                    "selected_path": None,
                    "is_loadable": False,
                    "error": None,
                }

                if not candidates:
                    dll_entry["error"] = "No candidate paths found"
                    self.strategy["drivers_found"][dll] = dll_entry
                    if dll.lower() == "wdpkcs.dll":
                        self.strategy["error_codes"].append(ErrorCode.WATCHDATA_RUNTIME_MISSING)
                        self.strategy["issues"].append(
                            "WatchData PROXKey runtime not installed "
                            "(expected under System32\\Watchdata\\...\\wdpkcs.dll). "
                            "No assets fallback for this vendor."
                        )
                        logger.warning("WatchData runtime missing — install PROXKey CSP to enable wdpkcs.dll")
                    continue

                loaded_one = False
                for path, source in candidates:
                    is_loadable, error = self._test_load_dll(str(path))
                    dll_entry["candidates"].append({
                        "path": str(path),
                        "source": source,
                        "is_loadable": is_loadable,
                        "error": error,
                    })

                    if is_loadable and not loaded_one:
                        loaded_one = True
                        abs_path = str(path.resolve())
                        dll_entry["selected_path"] = abs_path
                        dll_entry["is_loadable"] = True
                        dll_entry["source"] = source
                        available.append(abs_path)
                        if not self.strategy["selected_driver"]:
                            self.strategy["selected_driver"] = abs_path
                        logger.info(f"Available driver: {dll} from {source} -> {abs_path}")
                        if dll.lower() == "wdpkcs.dll":
                            watchdata_found = True
                    elif not is_loadable:
                        logger.debug(f"Driver candidate failed [{dll} @ {source}]: {error}")

                if not loaded_one:
                    dll_entry["error"] = "All candidates failed to load"
                    self.strategy["error_codes"].append(ErrorCode.DLL_LOAD_FAILED)
                    logger.error(f"Driver {dll}: no loadable candidate")
                    if dll.lower() == "wdpkcs.dll":
                        self.strategy["error_codes"].append(ErrorCode.WATCHDATA_RUNTIME_MISSING)
                        self.strategy["issues"].append(
                            "WatchData wdpkcs.dll present but failed to load. "
                            "Verify PROXKey CSP India V3.0 installation."
                        )

                self.strategy["drivers_found"][dll] = dll_entry

            if watchdata_requested and not watchdata_found:
                if ErrorCode.WATCHDATA_RUNTIME_MISSING not in self.strategy["error_codes"]:
                    self.strategy["error_codes"].append(ErrorCode.WATCHDATA_RUNTIME_MISSING)

            self.strategy["available_drivers"] = available

    def _test_load_dll(self, path: str):
        """اختبار حقيقي: هل الويندوز قادر على فتح الـ DLL؟"""
        try:
            # Prepend DLL directory so side-by-side companions resolve (WatchData install folder)
            driver_dir = str(Path(path).parent)
            old_path = os.environ.get("PATH", "")
            if driver_dir and driver_dir not in old_path:
                os.environ["PATH"] = driver_dir + os.pathsep + old_path

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.LoadLibraryW.restype = ctypes.c_void_p
            kernel32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]
            kernel32.FreeLibrary.argtypes = [ctypes.c_void_p]

            handle = kernel32.LoadLibraryW(path)
            if handle:
                kernel32.FreeLibrary(handle)
                return True, None
            err = ctypes.get_last_error()
            return False, f"LoadLibrary failed (WinError {err})"
        except Exception as e:
            return False, str(e)
