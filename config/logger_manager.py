import logging
from .paths import LOGS_PATH

def setup_global_logger(app_name: str):
    """
    تهيئة نظام السجلات الموحد للنسخة اللايت.
    يستخدم مسار LOGS_PATH المعرف في paths.py لضمان استمرارية السجلات في AppData.
    """
    try:
        # التأكد من وجود المجلد فوراً قبل محاولة فتح ملف السجل
        # هذا يمنع FileNotFoundError في حالة استدعاء اللوجر قبل ensure_dirs
        LOGS_PATH.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    log_file = LOGS_PATH / f"{app_name.lower()}.log"
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. File Handler (سجل كامل للدييباج)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 2. Console Handler (سجل مختصر للمستخدم/المطور)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Avoid duplicate console/file lines when setup is called more than once
    # (e.g. main.py then run_cli).
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # تقليل ضجيج المكتبات الخارجية
    logging.getLogger('PIL.Image').setLevel(logging.WARNING)