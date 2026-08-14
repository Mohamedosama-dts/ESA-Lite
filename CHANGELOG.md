# Changelog

All notable changes to ESA-Lite are documented here.

## Unreleased

### Windows Certificate Store

- After publishing the public cert to `CURRENT_USER\MY`, call `CryptFindCertificateKeyProvInfo` (silent) so the entry links to the token CSP/KSP (`HasPrivateKey=True` when middleware is present)
- Skip `CryptFind…` when EnterSafe CSP is not registered; never treat a failed key link as publish failure (avoids AV / false “publish failed”)
- Docs: ITIDA Web Signer `cmd=store` only lists certs with a private-key association; ITIDA has **no** PKCS#11 assets fallback
- **Verified (WatchData / PROXKey):** after ESA-Lite login, cert appears in ITIDA store picker and `cmd=sign` succeeds on ETA preprod when vendor CSP is installed
- **Verified (ePass / EnterSafe):** ITIDA `cmd=store` + `cmd=sign` on ETA preprod with ESA-Lite silent CSP/KSP/Calais registration only (no Feitian ePassManager UI)
- Logger: avoid duplicate console lines when `setup_global_logger` runs more than once

### Packaging / ePass middleware

- MSI installs `eps2003csp11` **x64 → System32** and **x86 → SysWOW64**
- MSI registers `EnterSafe ePass2003 CSP v1.0` (native + WOW), KSP, and Calais ATR mapping for ITIDA (32-bit)
- Bundled `assets/drivers/x86/` for SysWOW64; PKCS#11 assets fallback remains ESA-Lite-only
- Fix ExitDialog “Launch now”: condition used `WIXUI_EXITDIALOGOPTIONALCHECKBOXTEXT` (label) instead of `WIXUI_EXITDIALOGOPTIONALCHECKBOX` (checked state), so the app never started after install
## 2.1.0

Public-repo hardening on top of 2.0.0.

### Identity and OSS

- Product name **Electronic Signature Agent – Lite**; installer/tray/CI metadata aligned
- Apache-2.0 `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`
- Removed leftover Agent packaging (PyInstaller/Inno) and unused signing UI strings
- Offline toast (no remote audio URL)

### Hardware

- Multi-vendor PKCS#11 scan: ePass, EnterSafe, WatchData (install-only, no bundled `wdpkcs.dll`)
- Provider registry + `dll_path` on each token
- CLI health / available-drivers view

### Settings

- Writable data always under `%LOCALAPPDATA%\DTS\ESA-Lite`
- Atomic `user_settings.json` writes; corrupt files quarantined as `*.json.bad`
- Theme and language persist via the UI bridge (`set_theme`)
- `python main.py --print-runtime-paths`

### Windows Certificate Store

- Publish public cert to `CURRENT_USER\MY` after login
- Remove on logout or token disconnect
- Store errors are non-fatal

### Packaging and CI

- `packaging/` + [DEPLOY_ARTIFACT_CONTRACT.md](packaging/DEPLOY_ARTIFACT_CONTRACT.md)
- Release assets: `ESA_Lite_v2.1.0.exe`, `ESA_Lite_en.msi`, `ESA_Lite_ar.msi`
- GitHub Release on tag `v*`; no secret baking
- Runtime-path smoke after Nuitka

### Docs

- Public README, architecture, hardware, settings, WinCert
- Removed stale `structure.txt`

## 2.0.0 — baseline

Initial Lite edition: Vue 3 + pywebview UI, PKCS#11 engine, CLI, Nuitka + WiX packaging. Token display, PIN, and certificate view only.
