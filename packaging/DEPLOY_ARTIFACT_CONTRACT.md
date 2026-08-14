# Deploy release contract (ESA-Lite)

SSOT for scripts and humans that publish **ESA-Lite** binaries.

This is a **public** product. There is **no** secret baking (no NATS URL, no bus credentials).

Breaking changes to release asset **filenames** require a documented version bump and release-notes callout.

## What ESA-Lite provides

| Field | Stable value |
|--------|----------------|
| Product | ESA-Lite (display & management only) |
| Production source | **GitHub Release** on tag `v*` |
| Workflow | `ESA-Lite Build Pipeline` (`.github/workflows/build.yml`) |
| Release assets (3 files) | See table below |

### Release assets (Deploy units)

| Asset filename | Deploy unit |
|----------------|-------------|
| `ESA_Lite_v2.1.1.exe` | **ESA-Lite-Core-Executable** |
| `ESA_Lite_en.msi` | **ESA-Lite-Localized-MSIs** (EN) |
| `ESA_Lite_ar.msi` | **ESA-Lite-Localized-MSIs** (AR) |

When the product version changes, replace `2.1.1` in the EXE name to match `AppConfig.AGENT_VERSION` / the WiX `Product/@Version`. MSI **base** names stay `ESA_Lite_en.msi` / `ESA_Lite_ar.msi`.

CI still uploads Actions artifacts on `main` (7-day retention) for debugging. **They are not the production feed.**

## Consumer obligations

1. Pin an explicit tag (`v2.0.0`, `v2.1.1`, …).
2. Download the **three** assets by exact filename from that release.
3. If any asset is missing → **fail** (do not publish a partial set).
4. Do **not** use Actions artifacts as the production feed.

## Out of scope for this contract

- Burn bundle `ESA_Lite_Setup_v2.1.1.exe` / artifact `ESA-Lite-Final-Setup`
- Any signing-agent / NATS / secret injection

## Example pull

```bash
gh release download v2.1.1 -R Mohamedosama-dts/ESA-Lite \
  -p ESA_Lite_en.msi \
  -p ESA_Lite_ar.msi \
  -p ESA_Lite_v2.1.1.exe \
  -D /tmp/esa-lite

test -f /tmp/esa-lite/ESA_Lite_en.msi
test -f /tmp/esa-lite/ESA_Lite_ar.msi
test -f /tmp/esa-lite/ESA_Lite_v2.1.1.exe
```
