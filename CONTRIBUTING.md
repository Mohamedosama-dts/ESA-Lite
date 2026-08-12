# Contributing to ESA-Lite

ESA-Lite is a local USB token display and management app. Useful additions from the e-signature community (especially Egypt / ETA token users) are welcome.

## Useful contributions

- A token that does not show up: open a hardware issue with vendor, model, and PKCS#11 DLL name
- A new or corrected entry in `assets/config/vendors_map.json` (see [docs/HARDWARE.md](docs/HARDWARE.md))
- Arabic or English UI strings in `src/assets/locales/`
- UI or CLI fixes that stay inside display / PIN / certificate view
- Docs that match the running code

## Product identity

| Use | Do not use |
|-----|------------|
| **ESA-Lite** (product / window / tray / installer display) | “ESA Agent”, “ESA Agent Lite”, “ESA_Agent” in user-facing text |
| **Electronic Signature Agent – Lite** (full formal name) | Misspellings such as “Elecronic…” |
| Scope: local token **display & management** (login, PIN, view certificate) | Remote signing, NATS bus, job workers, or commercial agent protocol docs |

Keep WiX **UpgradeCode** and existing install folder identity (`ESA-Lite`) unless a deliberate breaking installer change is approved.

## What belongs in this repository

- PKCS#11 discovery, token UI/CLI, certificate view, PIN change
- Packaging, CI, and docs for a **public** Lite product
- Hardware/driver policy: see [docs/HARDWARE.md](docs/HARDWARE.md)
- Settings / AppData contract: see [docs/SETTINGS.md](docs/SETTINGS.md)
- Windows MY-store publish/remove: see [docs/WINCERT.md](docs/WINCERT.md)
- Packaging / release assets: see [packaging/README.md](packaging/README.md) and [packaging/DEPLOY_ARTIFACT_CONTRACT.md](packaging/DEPLOY_ARTIFACT_CONTRACT.md)
- Doc index: [docs/README.md](docs/README.md)

## What does not belong here

- Signing pipelines, remote bus clients, or secrets baked into binaries
- Leftover full-agent packaging (PyInstaller `.spec`, Inno Setup scripts)
- External network calls for trivial UX (e.g. remote toast sound URLs)

## Development basics

1. Python 3.11+ with a virtualenv; `pip install -r requirements.txt`
2. Node 20+; `npm install` then `npm run build` (UI lands in `interfaces/ui/dist`)
3. Run GUI: `python main.py` — CLI: `python main.py --cli`

## Pull requests

- Keep changes focused; match existing code style
- Prefer Arabic/English UI strings via `src/assets/locales/`
- Do not commit `.venv/`, `node_modules/`, `dist_bin/`, logs, or local `user_settings.json`

## Security reports

See [SECURITY.md](SECURITY.md). Do not open public issues for undisclosed vulnerabilities.
