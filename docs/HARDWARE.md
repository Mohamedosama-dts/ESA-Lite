# ESA-Lite hardware policy

ESA-Lite talks to USB cryptographic tokens through **PKCS#11 DLLs**. There is no hash-signing path in this product.

## Supported libraries

| DLL | Typical vendor | Discovery | Assets fallback (ESA-Lite only) |
|-----|----------------|-----------|----------------------------------|
| `eps2003csp11.dll` | Feitian / ePass 2003 | System32, then bundled assets | Yes |
| `entersafe_p11.dll` | EnterSafe | System32, then assets **if the file is present** | Yes |
| `wdpkcs.dll` | WatchData PROXKey | Vendor install under System32 only | **No** |

Source of truth for the scan list is `ConfigLoader.known_drivers` (defaults above). `AppConfig.TARGET_DLLS` is a deprecated mirror for external readers.

## Asymmetric fallback (ESA-Lite PKCS#11 only)

1. Probe vendor-specific install globs (WatchData: `Watchdata/PROXKey CSP India V3.0/wdpkcs.dll` and `Watchdata/*/wdpkcs.dll`).
2. Probe `System32\{dll}`.
3. Probe `assets/drivers/{arch}/{dll}` **only** when `allows_assets_fallback(dll)` is true.

This fallback is **only for ESA-Lite** (scan / PIN / read public cert). External Windows apps such as **ITIDA Web Signer have no assets fallback** — they load the vendor **CSP/KSP** from the OS registration (`System32` / `SysWOW64` + registry).

WatchData middleware is **install-only**. ESA-Lite does not ship `wdpkcs.dll` in a public tree (vendor license). If the runtime is missing, health check records `WATCHDATA_RUNTIME_MISSING` and continues with other vendors.

## Windows apps and ITIDA Web Signer

ESA-Lite uses PKCS#11 for display, PIN, and reading the public certificate. Publishing into `CURRENT_USER\MY` for Windows/ITIDA also needs the vendor **CSP/KSP** so Windows can set `HasPrivateKey` on that store entry. PKCS#11 alone does not satisfy ITIDA Web Signer `cmd=store` / `cmd=sign`. See [WINCERT.md](WINCERT.md).

### ePass / EnterSafe (shipped by ESA-Lite MSI)

The MSI (no Feitian `ePassManager` UI) installs:

| Piece | Location / key |
|-------|----------------|
| x64 DLL | `System32\eps2003csp11.dll` (+ `_s`) |
| x86 DLL | `SysWOW64\eps2003csp11.dll` (+ `_s`) — required because **ITIDA Web Signer is 32-bit** |
| CSP | `EnterSafe ePass2003 CSP v1.0` (native + `WOW6432Node`) → Image Path = `eps2003csp11.dll` |
| KSP | `EnterSafe ePass2003 Key Storage Provider` |
| Calais | `SmartCards\ePass2003` ATR → CSP (native + WOW) |

Signing may show the **vendor CSP PIN/confirm UI** (CryptoAPI), not an ESA-Lite dialog.

**Verified:** ITIDA `cmd=store` + `cmd=sign` on ETA preprod without Feitian management UI (registry + OS DLLs only).

### WatchData + PROXKey

Verified end-to-end with ITIDA when the vendor PROXKey CSP runtime is installed (ESA-Lite does not redistribute `wdpkcs.dll`).

## Scope vs the commercial signing agent

Lite reuses multi-DLL discovery, a provider registry, and per-token `dll_path` so display and PIN/cert management work across vendors.

It does **not** include hash signing, worker processes, a remote job bus, or a local HTTP API. Those belong to a separate product.

## Bundled assets

| Folder | Role |
|--------|------|
| `assets/drivers/x64/` | ESA-Lite PKCS#11 fallback **and** MSI → System32 |
| `assets/drivers/x86/` | MSI → SysWOW64 for 32-bit CryptoAPI clients (ITIDA). Not used by the x64 ESA-Lite process |

Do not add WatchData binaries here.

CLI option **7** prints available drivers and health issues (`python main.py --cli`).
