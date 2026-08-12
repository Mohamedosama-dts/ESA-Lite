import logging
from threading import RLock, Thread, Event # استيراد RLock و Event
from typing import Optional, Tuple

# استيراد المكونات الأساسية فقط
from core.engine import Engine
from core.inventory import TokenInventory as Inventory
from core.windows_monitor import WindowsMonitor
from core.utils.physical_lock_manager import PhysicalLockManager
from core.strategy_manager import StrategyManager
from core.utils.health_check import HealthCheck
from config.app_config import AppConfig
from config.config_loader import ConfigLoader
from core.utils.defender_hint import register_with_event_log

logger = logging.getLogger("ESA-Lite.Scope")

class ApplicationScope:
    """
    ApplicationScope (Lite Version)
    الحاوية المركزية لإدارة دورة حياة المكونات الأساسية فقط.
    تم حذف: BusOrchestrator, JobDispatcher, API Server, Redis.
    WinCertStore يُستدعى من Inventory عند login / logout / disconnect.
    """
    _instance_lock = RLock()
    
    # مراجع المكونات (Singletons)
    _config: Optional[AppConfig] = None
    _config_loader: Optional[ConfigLoader] = None
    _inventory: Optional[Inventory] = None
    _initialization_complete_event: Optional[Event] = None # لإشارة اكتمال التهيئة الخلفية
    _engine: Optional[Engine] = None
    _monitor: Optional[Optional[WindowsMonitor]] = None
    _lock_manager: Optional[PhysicalLockManager] = None
    _strategy_manager: Optional[StrategyManager] = None
    _health_check: Optional[HealthCheck] = None
    _health_report: Optional[dict] = None # مخزن لنتائج الفحص لمنع التكرار
    _is_shutting_down = False

    @classmethod
    def _get_singleton(cls, attr_name, factory_func):
        """مساعد لضمان إنشاء نسخة واحدة فقط (Thread-safe)"""
        if getattr(cls, attr_name) is None:
            with cls._instance_lock:
                if getattr(cls, attr_name) is None:
                    instance = factory_func()
                    setattr(cls, attr_name, instance)
        return getattr(cls, attr_name)

    @classmethod
    def get_config(cls) -> AppConfig:
        return cls._get_singleton("_config", lambda: AppConfig())

    @classmethod
    def get_config_loader(cls) -> ConfigLoader:
        return cls._get_singleton("_config_loader", lambda: ConfigLoader())

    @classmethod
    def get_lock_manager(cls) -> PhysicalLockManager:
        # النسخة الجديدة التي تستخدم threading.Lock داخلياً
        return cls._get_singleton("_lock_manager", lambda: PhysicalLockManager())

    @classmethod
    def get_inventory(cls) -> Inventory:
        return cls._get_singleton("_inventory", lambda: Inventory())

    @classmethod
    def get_strategy_manager(cls) -> StrategyManager:
        return cls._get_singleton(
            "_strategy_manager", 
            # نمرر التقرير المخزن (إن وجد) لمنع إعادة تشغيل الفحص
            lambda: StrategyManager(cls.get_config(), cls.get_config_loader(), cls._health_report)
        )

    @classmethod
    def get_health_check(cls) -> HealthCheck:
        return cls._get_singleton("_health_check", lambda: HealthCheck(cls.get_config_loader()))

    @classmethod
    def get_engine(cls) -> Engine:
        def create_engine():
            inventory = cls.get_inventory()
            lock_manager = cls.get_lock_manager()
            strategy_manager = cls.get_strategy_manager()
            # المحرك الآن يعتمد على الـ Inventory والأقفال والاستراتيجية
            return Engine(inventory=inventory, lock_manager=lock_manager, strategy_manager=strategy_manager)
        return cls._get_singleton("_engine", create_engine)

    @classmethod
    def get_monitor(cls) -> WindowsMonitor:
        def create_monitor():
            engine = cls.get_engine()
            inventory = cls.get_inventory()
            # المونيتور يحتاج للمحرك والمخزن معاً للقيام بعملية المزامنة
            return WindowsMonitor(engine=engine, inventory=inventory)
        return cls._get_singleton("_monitor", create_monitor)

    @classmethod
    def _background_init_task(cls):
        """مهمة تهيئة الخدمات الأساسية في الخلفية"""
        logger.info("Starting background initialization...")
        try:
            register_with_event_log()

            cls._health_report = cls.get_health_check().run_full_check()
            if cls._health_report.get("status") == "CRITICAL":
                logger.error("Critical system error: %s", cls._health_report.get("issues"))

            monitor = cls.get_monitor()
            monitor.start()

            cls.get_engine().list_tokens()

            logger.info("Core services ready.")
        except Exception as e:
            logger.critical(f"Fatal error during background initialization: {e}", exc_info=True)
        finally:
            if cls._initialization_complete_event:
                cls._initialization_complete_event.set() # إشارة اكتمال التهيئة

    @classmethod
    def initialize_lite_services(cls) -> Event:
        """تهيئة الخدمات الأساسية للنسخة اللايت بالترتيب الصحيح في خيط خلفي."""
        with cls._instance_lock:
            if cls._initialization_complete_event is None:
                # إنشاء الحدث هنا يضمن عدم رجوع None أبداً
                cls._initialization_complete_event = Event()
                init_thread = Thread(target=cls._background_init_task, daemon=True)
                init_thread.start()
                logger.info("Background initialization thread started.")
            else:
                logger.info("Background initialization already in progress or complete.")
            return cls._initialization_complete_event

    @classmethod
    def shutdown(cls):
        """إغلاق الموارد بشكل نظيف"""
        with cls._instance_lock:
            if cls._is_shutting_down:
                return
            cls._is_shutting_down = True

        logger.info("Shutting down ESA-Lite services...")
        try:
            if cls._monitor:
                cls._monitor.stop()
            if cls._lock_manager:
                cls._lock_manager.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        logger.info("Shutdown complete.")
