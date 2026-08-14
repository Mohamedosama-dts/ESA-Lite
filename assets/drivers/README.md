# Bundled ePass / EnterSafe drivers

## ESA-Lite PKCS#11 fallback (app only)

Place **x64** DLLs under `x64/` for ESA-Lite’s own scan when `System32` has no copy.

- **Allowed:** ePass / EnterSafe family (`eps2003csp11.dll`, optional `entersafe_p11.dll`).
- **Not allowed:** WatchData `wdpkcs.dll` — users must install PROXKey CSP. Health check will warn if it is missing.

External apps (ITIDA Web Signer, etc.) **do not** use this folder.

## Windows / ITIDA CSP (MSI)

| Folder | MSI destination | Consumers |
|--------|-----------------|-----------|
| `x64/` | `System32` | 64-bit CryptoAPI, ESA-Lite PKCS#11 |
| `x86/` | `SysWOW64` | **32-bit** CryptoAPI (ITIDA Web Signer). Must be real PE **x86**, not a copy of the x64 file |

The MSI also registers EnterSafe CSP (native + WOW), KSP, and Calais `SmartCards\ePass2003` ATR → CSP. See [docs/HARDWARE.md](../../docs/HARDWARE.md).
