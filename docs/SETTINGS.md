# ESA-Lite settings and runtime paths

## `user_settings.json`

| Key | Default | Meaning |
|-----|---------|---------|
| `agent_id` | UUID (created once) | Local install identity |
| `language` | `ar` | UI language (`ar` or `en`) |
| `theme` | `light` | UI theme (`light` or `dark`) |

**Location (always writable AppData, never next to the EXE extract):**

`%LOCALAPPDATA%\DTS\ESA-Lite\config\user_settings.json`

Same folder holds `vendors_map.json`. Logs: `%LOCALAPPDATA%\DTS\ESA-Lite\logs\`. Temp certs: `%LOCALAPPDATA%\DTS\ESA-Lite\temp\`.

This applies to **source** and **frozen (Nuitka)** runs. `BASE_DIR` (assets / UI dist) may be the repo or the onefile unpack dir; `DATA_DIR` must not.

## Corrupt file recovery

If `user_settings.json` is not valid JSON:

1. Rename it to `user_settings.json.bad` (best-effort).
2. Recreate the default template.
3. Continue startup; do not crash.

Writes use a temp file (`user_settings.json.tmp`) then `os.replace` so a crash mid-write cannot leave a half-file as the live settings.

## UI bridge

| Method | Role |
|--------|------|
| `get_current_translations()` | Returns `lang`, `theme`, `version`, `prefix` for first paint |
| `toggle_language()` | Flip `ar`/`en` and persist `language` |
| `set_theme(theme)` | Persist `light` or `dark` |

The Vue app must apply `theme` from the bridge on boot and on toggle — never local-only.

## Path smoke

`python main.py --print-runtime-paths` prints JSON with `IS_FROZEN`, `BASE_DIR`, `DATA_DIR`, `USER_SETTINGS`, `LOGS_PATH`, `TEMP_DIR`. `DATA_DIR` must contain `DTS\ESA-Lite` and must not contain `onefile_`.
