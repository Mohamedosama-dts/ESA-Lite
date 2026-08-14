# ESA-Lite packaging

Build the Vue UI, freeze with Nuitka, then produce localized MSI installers and an optional Burn bootstrapper.

There is **no** secret baking. Tags `v*` publish a GitHub Release with the three contract assets.

## Product identity

| Surface | Value |
|---------|--------|
| Product / Bundle name | ESA-Lite |
| Program Files / Start Menu | `ESA-Lite` |
| Installed EXE | `ESA_Lite.exe` |
| Autorun registry name | `ESA_Lite` |
| Runtime AppData | `%LOCALAPPDATA%\DTS\ESA-Lite` |
| MSI UpgradeCode | `e7b2f1a4-1234-4567-89ab-cdef12345678` (unchanged) |
| Bundle UpgradeCode | `f8c3d4e5-1234-4abc-def1-234567890abc` (unchanged) |
| Contract EXE | `dist_bin\ESA_Lite_v2.1.1.exe` |
| Contract MSIs | `dist_bin\ESA_Lite_en.msi`, `dist_bin\ESA_Lite_ar.msi` |
| Burn (out of contract) | `dist_bin\ESA_Lite_Setup_v2.1.1.exe` |

Writable data is always AppData. Nuitka `onefile_*` unpack is read-only assets only. See [docs/SETTINGS.md](../docs/SETTINGS.md).

**ePass middleware (MSI):** `setup.wxs` copies `assets/drivers/x64` → System32 and `assets/drivers/x86` → SysWOW64, and registers EnterSafe CSP/KSP + Calais ATR so **ITIDA** (32-bit) can sign without Feitian UI. PKCS#11 assets fallback inside the app does not replace that OS registration — see [docs/HARDWARE.md](../docs/HARDWARE.md).

**CI smoke:** after Nuitka, the workflow runs `ESA_Lite_v2.1.1.exe --print-runtime-paths` (JSON via `ESA_PATHS_OUT`). Success requires `IS_FROZEN`, `DATA_DIR` under `...\DTS\ESA-Lite`, and no `\onefile_`.

**CI speed:** PRs build UI + EXE + smoke only. MSI/Bundle run on push to `main`/`master` or tag `v*`.

## Requirements

- Windows 10/11 x64
- Node.js 20+
- Python 3.11+
- Nuitka 4.1.3 + zstandard 0.25.0 (CI pins these)
- WiX Toolset v3 (`candle` / `light` on PATH) for MSI/bundle

## Local build order

From the repository root:

1. `packaging\build_ui.bat` — Vite → `interfaces\ui\dist`
2. `packaging\build_exe.bat` — Nuitka → `dist_bin\ESA_Lite_v2.1.1.exe`
3. Optional smoke: `dist_bin\ESA_Lite_v2.1.1.exe --print-runtime-paths`
4. WiX (from repo root):

```bat
set REPO_ROOT=%CD%
candle -ext WixUIExtension -ext WixUtilExtension -dRepoRoot=%REPO_ROOT% -dLanguage=1033 -dLicenseRtf=%REPO_ROOT%\assets\license_en.rtf packaging\wix\setup.wxs -o packaging\wix\setup_en.wixobj
light -ext WixUIExtension -ext WixUtilExtension -loc packaging\wix\en-US.wxl packaging\wix\setup_en.wixobj -o dist_bin\ESA_Lite_en.msi

candle -ext WixUIExtension -ext WixUtilExtension -dRepoRoot=%REPO_ROOT% -dLanguage=1025 -dLicenseRtf=%REPO_ROOT%\assets\license_ar.rtf packaging\wix\setup.wxs -o packaging\wix\setup_ar.wixobj
light -ext WixUIExtension -ext WixUtilExtension -loc packaging\wix\ar-SA.wxl packaging\wix\setup_ar.wixobj -o dist_bin\ESA_Lite_ar.msi

candle -ext WixBalExtension -dRepoRoot=%REPO_ROOT% packaging\wix\bundle.wxs -o packaging\wix\bundle.wixobj
light -ext WixBalExtension packaging\wix\bundle.wixobj -o dist_bin\ESA_Lite_Setup_v2.1.1.exe
```

Asset names: [`DEPLOY_ARTIFACT_CONTRACT.md`](DEPLOY_ARTIFACT_CONTRACT.md).

## Layout

```text
packaging/
  build_ui.bat
  build_exe.bat
  README.md
  DEPLOY_ARTIFACT_CONTRACT.md
  wix/
    setup.wxs
    bundle.wxs
    en-US.wxl
    ar-SA.wxl
```
