# ESA-Lite

**Electronic Signature Agent – Lite** is an open-source Windows desktop app for **USB cryptographic token display and management**.

It lists connected USB tokens, verifies PIN login/logout, supports PIN change, and opens the public certificate in the Windows cert viewer. After login it publishes that **public** certificate to the current user’s Personal store and removes it on logout or unplug. Arabic/English UI and light/dark theme persist under AppData. Diagnostic CLI: `python main.py --cli`.

It does not sign hashes, run job queues, expose a local HTTP API, or talk to a commercial signing backend. A separate commercial product covers those workloads.

This repo is for people in Egypt (and elsewhere) who use USB tokens for e-invoicing and e-signature and want a small local tool they can inspect and extend. Token reports, vendor maps, and translations are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

**للعربية:** ESA-Lite برنامج مجاني محلي لإدارة توكن التوقيع الإلكتروني على ويندوز (عرض، PIN، شهادة). مش خدمة توقيع عن بُعد. لو توكنك مش ظاهر، أو عندك تعريف/ترجمة تنفع غيرك، افتح issue أو PR.

[License (Apache 2.0)](LICENSE) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Requirements

- Windows 10/11 x64
- Smart Card service (`SCardSvr`)
- A supported PKCS#11 token (see [docs/HARDWARE.md](docs/HARDWARE.md))

For WatchData tokens, install the vendor **PROXKey** runtime. ESA-Lite does not ship `wdpkcs.dll`.

## Install

Release assets (exact names):

| File | Role |
|------|------|
| `ESA_Lite_en.msi` / `ESA_Lite_ar.msi` | Localized installer |
| `ESA_Lite_v2.1.1.exe` | Portable / core executable |

See [packaging/DEPLOY_ARTIFACT_CONTRACT.md](packaging/DEPLOY_ARTIFACT_CONTRACT.md). Tags `v*` publish a GitHub Release with those three files.

Settings and logs live in `%LOCALAPPDATA%\DTS\ESA-Lite\` ([docs/SETTINGS.md](docs/SETTINGS.md)).

## Build from source

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

npm install
npm run build

python main.py
python main.py --cli
python main.py --print-runtime-paths
```

Full Nuitka + MSI: [packaging/README.md](packaging/README.md) (`packaging\build_ui.bat` then `packaging\build_exe.bat`).

## Repository layout

```text
main.py                 Entry (GUI, --cli, --tray, --print-runtime-paths)
src/                    Vue 3 + Vite UI
interfaces/ui/          pywebview host + built dist/
interfaces/cli/         Diagnostic CLI
core/                   Engine, inventory, PKCS#11, health, WinCertStore
config/                 Paths, settings, logging
models/                 Pydantic contracts
assets/                 Icons, EULA, bundled ePass PKCS#11 fallbacks
packaging/              WiX, build scripts, release contract
docs/                   Architecture, hardware, settings, WinCert
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

Copyright 2026 DTS — Digital Transformation Services.  
Licensed under the [Apache License 2.0](LICENSE).
