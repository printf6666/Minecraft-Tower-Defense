@echo off
cd /d "%~dp0"

echo ========================================
echo   MCTD Auto Build Script
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found. Install Python and add to PATH.
    pause
    exit /b 1
)

echo [1/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/3] Building...
python -m PyInstaller --onefile --noconsole --name MCTD ^
    --add-data "bgm;bgm" ^
    --add-data "debuff;debuff" ^
    --add-data "enchantment;enchantment" ^
    --add-data "enemy;enemy" ^
    --add-data "sound;sound" ^
    --add-data "tower;tower" ^
    --add-data "Minecraft.ttf;." ^
    --add-data "seed.json;." ^
    main.py
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Done
for %%F in (dist\MCTD.exe) do echo     Output: dist\MCTD.exe (%%~zF bytes)
pause
