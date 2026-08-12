# ESA-Lite hardware policy

ESA-Lite talks to USB cryptographic tokens through **PKCS#11 DLLs**. There is no hash-signing path in this product.

## Supported libraries

| DLL | Typical vendor | Discovery | Assets fallback |
|-----|----------------|-----------|-----------------|
| `eps2003csp11.dll` | Feitian / ePass 2003 | System32, then bundled assets | Yes |
| `entersafe_p11.dll` | EnterSafe | System32, then assets **if the file is present** | Yes |
| `wdpkcs.dll` | WatchData PROXKey | Vendor install under System32 only | **No** |

Source of truth for the scan list is `ConfigLoader.known_drivers` (defaults above). `AppConfig.TARGET_DLLS` is a deprecated mirror for external readers.

## Asymmetric fallback

1. Probe vendor-specific install globs (WatchData: `Watchdata/PROXKey CSP India V3.0/wdpkcs.dll` and `Watchdata/*/wdpkcs.dll`).
2. Probe `System32\{dll}`.
3. Probe `assets/drivers/{arch}/{dll}` **only** when `allows_assets_fallback(dll)` is true.

WatchData middleware is **install-only**. ESA-Lite does not ship `wdpkcs.dll` in a public tree (vendor license). If the runtime is missing, health check records `WATCHDATA_RUNTIME_MISSING` and continues with other vendors.

## Scope vs the commercial signing agent

Lite reuses multi-DLL discovery, a provider registry, and per-token `dll_path` so display and PIN/cert management work across vendors.

It does **not** include hash signing, worker processes, a remote job bus, or a local HTTP API. Those belong to a separate product.

## Bundled assets

`assets/drivers/x64/` may contain ePass-family PKCS#11 files used as fallback when the OS copy is missing. Do not add WatchData binaries here.

CLI option **7** prints available drivers and health issues (`python main.py --cli`).
