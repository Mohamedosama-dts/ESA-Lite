import json
import logging
import multiprocessing
import sys
import ctypes
from ctypes import wintypes

logger = logging.getLogger("main")

# حفظ مرجع الميوتكس لمنع جمعه بواسطة Garbage Collector
_single_instance_mutex = None

def is_already_running():
    """التحقق من وجود نسخة تعمل من التطبيق باستخدام Windows Mutex"""
    global _single_instance_mutex
    try:
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]

        # Global\\ تجعل الميوتكس متاحاً عبر جلسات المستخدمين المختلفة (أكثر أماناً للهاردوير)
        mutex_name = "Global\\ESA_Lite_Single_Instance_2026"
        _single_instance_mutex = k32.CreateMutexW(None, False, mutex_name)
        return ctypes.get_last_error() == 183 # ERROR_ALREADY_EXISTS
    except Exception as e:
        return False

def _print_runtime_paths_and_exit():
    """CI / packaging smoke: emit path resolution then exit (no GUI, no mutex)."""
    import os
    from pathlib import Path
    from config.paths import runtime_paths_report

    payload = json.dumps(runtime_paths_report(), ensure_ascii=False)
    out = os.environ.get("ESA_PATHS_OUT", "").strip()
    out_path = Path(out) if out else Path(os.environ.get("TEMP", ".")) / "esa_lite_runtime_paths.json"
    out_path.write_text(payload + "\n", encoding="utf-8")
    try:
        print(payload)
        print(f"ESA_PATHS_OUT_FILE={out_path}", flush=True)
    except Exception:
        pass
    sys.exit(0)

def main():
    if "--print-runtime-paths" in sys.argv:
        _print_runtime_paths_and_exit()

    if is_already_running():
        sys.exit(0)

    # 1. إنشاء المجلدات أولاً وقبل كل شيء
    from config.paths import ensure_dirs, runtime_paths_report
    ensure_dirs()

    # تهيئة اللوجر أولاً لضمان تسجيل أي خطأ في الـ Scope
    is_cli = "--cli" in sys.argv
    start_in_tray = "--tray" in sys.argv

    from config.logger_manager import setup_global_logger
    setup_global_logger("CLI-DEBUG" if is_cli else "AGENT-UI")

    report = runtime_paths_report()
    logger.info(
        "Runtime paths: IS_FROZEN=%s DATA_DIR=%s USER_SETTINGS=%s",
        report["IS_FROZEN"],
        report["DATA_DIR"],
        report["USER_SETTINGS"],
    )

    if is_cli:
        from interfaces.cli.cli_app import run_cli
        run_cli()
    else:
        from interfaces.ui.ui_main import start_gui
        start_gui(minimized=start_in_tray)

if __name__ == "__main__":
    # استخدام multiprocessing مباشرة كما في النسخة المستقرة
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupt received (Ctrl+C).")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        logging.critical(f"Fatal startup error: {e}", exc_info=True)
        input("\n[PAUSE] Press Enter to close this window...")
    finally:
        try:
            from core.containers import ApplicationScope
            ApplicationScope.shutdown()
        except:
            pass