@echo off
setlocal
cd /d "%~dp0.."

set UI_OUTPUT=interfaces\ui\dist
echo ---------------------------------------------------
echo ESA-Lite Frontend Production Build
echo ---------------------------------------------------

echo [1/3] Installing Dependencies...
call npm install
if errorlevel 1 exit /b 1

echo [2/3] Compiling Vue Application (Vite)...
call npm run build
if errorlevel 1 exit /b 1

echo [3/3] Syncing Assets for Python Backend...
if not exist "%UI_OUTPUT%\locales" mkdir "%UI_OUTPUT%\locales"
xcopy /y /s "src\assets\locales\*" "%UI_OUTPUT%\locales\"

echo.
echo SUCCESS: UI is ready for Nuitka packaging.
endlocal
pause
