# ESA-Lite architecture

Linear path, single process:

```text
Vue UI  →  UIBridge (pywebview)  →  Engine  →  StrategyManager  →  PKCS#11 DLLs
                                      ↓
                               TokenInventory
                                      ↓
                          WinCertStore (MY, public cert only)
```

USB insert/remove is observed by `WindowsMonitor` (`winscard`) and synced through the Engine into inventory.

## Lifecycle (`ApplicationScope`)

`core/containers.py` holds thread-safe singletons: config, inventory, health check, strategy manager, engine, monitor, physical locks.

1. `main.py` creates AppData dirs and logging.
2. GUI calls `initialize_lite_services()` (health check + monitor on a background thread).
3. CLI constructs the engine directly (no tray / monitor loop required).
4. `shutdown()` stops the monitor and releases locks.

There is no remote bus, job dispatcher, or local HTTP server in this process.

## UI bridge

`interfaces/ui/ui_main.py` exposes: `get_tokens`, `login`, `logout`, `view_cert`, `change_pin`, `toggle_language`, `set_theme`, `get_current_translations`, `hide_to_tray`, `close_app`.

Theme and language are persisted via `ConfigLoader` ([SETTINGS.md](SETTINGS.md)).

## Hardware

`HealthCheck` collects every loadable PKCS#11 path (`available_drivers`). `StrategyManager` registers one provider per path and stamps `dll_path` on each scanned token so PIN/cert ops hit the right library. Policy: [HARDWARE.md](HARDWARE.md).

## Windows certificates

After login, inventory publishes the public DER to `CURRENT_USER\MY`. Logout and disconnect remove it. Failures are logged only. [WINCERT.md](WINCERT.md).
