@echo off
setlocal
cd /d "%~dp0.."

echo ---------------------------------------------------
echo ESA-Lite Nuitka Native Compilation (v2.1.1)
echo ---------------------------------------------------
echo NOTE: Flags mirror .github/workflows/build.yml except
echo       --windows-console-mode=attach (CI uses disable).
echo       No secrets are baked into this binary.
echo ---------------------------------------------------

if exist .venv\Scripts\activate (
    echo [1/2] Activating virtual environment...
    call .venv\Scripts\activate
) else (
    echo [!] Warning: .venv not found. Using system Python...
)

set NUITKA_ACCEPT_DOWNLOADS=yes

echo [2/2] Starting Nuitka build process...
python -m nuitka ^
    --accept-downloads ^
    --standalone ^
    --onefile ^
    --python-flag=no_docstrings ^
    --python-flag=no_asserts ^
    --include-data-dir=assets=assets ^
    --include-data-dir=interfaces/ui/dist=interfaces/ui/dist ^
    --include-package=pystray ^
    --include-package=PIL ^
    --include-package=cryptography ^
    --include-package=webview ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=pydoc ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=webview.platforms.android ^
    --nofollow-import-to=webview.platforms.cocoa ^
    --nofollow-import-to=webview.platforms.gtk ^
    --nofollow-import-to=webview.platforms.qt ^
    --disable-plugin=pywebview ^
    --windows-console-mode=attach ^
    --windows-icon-from-ico=assets/icon.ico ^
    --output-dir=dist_bin ^
    --output-filename=ESA_Lite_v2.1.1 ^
    --include-windows-runtime-dlls=yes ^
    --jobs=3 ^
    --windows-company-name=DTS ^
    --windows-product-name=ESA-Lite ^
    --windows-file-description="Electronic Signature Agent - Lite" ^
    --windows-product-version=2.1.1 ^
    --windows-file-version=2.1.1 ^
    --copyright="Copyright (c) 2026 DTS Digital Transformation Services" ^
    --remove-output ^
    main.py

if errorlevel 1 (
    echo BUILD FAILED
    endlocal
    exit /b 1
)

echo.
echo SUCCESS: dist_bin\ESA_Lite_v2.1.1.exe
echo Optional smoke: dist_bin\ESA_Lite_v2.1.1.exe --print-runtime-paths
endlocal
pause
