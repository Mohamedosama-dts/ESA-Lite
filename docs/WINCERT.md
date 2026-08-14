# Windows Certificate Store (MY)

ESA-Lite publishes the token’s **public** X.509 certificate into the current user’s Personal store (`CURRENT_USER\MY`) after login. No private key is exported from the token.

After the DER is added, ESA-Lite calls Windows **`CryptFindCertificateKeyProvInfo`** (silent, user keyset) so the store entry is linked to the vendor **CSP/KSP** that holds the matching key on the smart card. That sets `HasPrivateKey=True` without copying the key off the token.

If the EnterSafe CSP is not registered, ESA-Lite **skips** `CryptFindCertificateKeyProvInfo` (avoids faults when only PKCS#11 assets fallback is present) and leaves the public cert in MY with `HasPrivateKey=False`.

Apps such as **ITIDA Web Signer** (`https://localhost:60025/`, `cmd=store`) only list certificates with a private-key association. A public-only MY entry is invisible to that picker. ITIDA is a **32-bit** process: it needs the CSP under the WOW provider view and `SysWOW64` DLLs — ESA-Lite’s `assets/drivers` PKCS#11 fallback does **not** help ITIDA.

## Contract

| Event | Action |
|-------|--------|
| Successful **login** and `certificate_der` is available | `WinCertStore.publish_certificate(der)` → add DER, then best-effort key-provider link |
| **Logout** or **PIN change** (which logs out) | `WinCertStore.remove_certificate(subject)` |
| Token **disconnect** (USB unplug / scan miss) | `WinCertStore.remove_certificate(subject)` if subject is known |

Failures (store locked, access denied, cert not found, CSP missing, link AV) are **logged only**. A successful DER add still counts as publish success even if the key link fails. Login, logout, PIN, and the UI must still succeed.

## Requirements for key linking

- Token plugged in at login time
- Smart-card **CSP or KSP** registered for Windows CryptoAPI (PKCS#11 alone is not enough)
- **ePass:** ESA-Lite MSI registers `EnterSafe ePass2003 CSP v1.0`, KSP, and Calais ATR mapping (x64 + x86). No Feitian management UI required.
- **WatchData:** PROXKey CSP runtime from the vendor ([HARDWARE.md](HARDWARE.md))

During ITIDA `cmd=sign`, Windows may show the **vendor CSP PIN/confirm** dialog. That is expected.

## Verified hardware

| Vendor / DLL | Middleware | ITIDA `cmd=store` | ITIDA `cmd=sign` |
|--------------|------------|-------------------|------------------|
| WatchData (`wdpkcs.dll`) | PROXKey CSP India V3.0 | Pass | Pass (ETA preprod, 2026-08-14) |
| ePass (`eps2003csp11.dll`) | EnterSafe CSP/KSP + Calais (ESA-Lite MSI / silent registry; no ePassManager) | Pass | Pass (ETA preprod, 2026-08-14) |

## Privacy / permissions

- Only the public certificate is written to the user store; the private key stays on the token.
- No elevation is required for `CURRENT_USER\MY`.
- Removing the token or logging out removes the published cert (best-effort).

## Verify

After login (PowerShell):

```powershell
Get-ChildItem Cert:\CurrentUser\My |
  Where-Object { $_.Subject -match 'YourCN' } |
  Select-Object Subject, Thumbprint, HasPrivateKey, NotAfter
```

Expect `HasPrivateKey` = `True` when CSP/KSP is registered.

ITIDA: trigger a signing flow that calls `cmd=store`, decode the base64 payload, and confirm the same thumbprint appears; then `cmd=sign`.

After logout or unplug: the same subject should be gone (or a warning in the log if Windows refused the delete).
