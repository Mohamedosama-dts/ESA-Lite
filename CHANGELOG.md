# Changelog

All notable changes to ESA-Lite are documented here.

## 2.0.0 — baseline

Initial Lite edition: Vue 3 + pywebview UI, PKCS#11 engine, CLI, Nuitka + WiX packaging. Token display, PIN, and certificate view only.

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
