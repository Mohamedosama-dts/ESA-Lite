# ESA-Lite documentation

Public docs for a **display and management** Windows token app. Do not document commercial signing-agent protocols, remote buses, or secrets.

| Doc | Audience |
|-----|----------|
| [../README.md](../README.md) | Users and new contributors |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Developers |
| [HARDWARE.md](HARDWARE.md) | Token / PKCS#11 support |
| [SETTINGS.md](SETTINGS.md) | AppData, theme, language |
| [WINCERT.md](WINCERT.md) | Windows MY store |
| [../packaging/README.md](../packaging/README.md) | Local build / MSI |
| [../packaging/DEPLOY_ARTIFACT_CONTRACT.md](../packaging/DEPLOY_ARTIFACT_CONTRACT.md) | Release asset names |
| [../CHANGELOG.md](../CHANGELOG.md) | What shipped |

## Must not appear in public docs

- Remote signing job formats, bus subjects, or baked URLs  
- Secret names used only by the commercial agent  
- Stale stack names (Webpack, “signing logic” in the Lite engine)
