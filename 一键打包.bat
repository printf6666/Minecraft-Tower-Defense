@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo   MCTD Auto Build Script
echo ========================================

REM ============================================================
REM  Find a Python that has BOTH pygame and pyinstaller installed.
REM  Order: MCTD_PYTHON env var -> D:\pytools -> python in PATH
REM ============================================================
set "PY="

if defined MCTD_PYTHON (
    call :check_python "!MCTD_PYTHON!"
    if not errorlevel 1 set "PY=!MCTD_PYTHON!"
)

if not defined PY (
    if exist "D:\pytools\python.exe" (
        call :check_python "D:\pytools\python.exe"
        if not errorlevel 1 set "PY=D:\pytools\python.exe"
    )
)

if not defined PY (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PY (
            call :check_python "%%P"
            if not errorlevel 1 set "PY=%%P"
        )
    )
)

if not defined PY (
    echo [ERROR] No usable Python found ^(needs pygame + pyinstaller^).
    echo.
    echo   - Point to your interpreter with:
    echo       set MCTD_PYTHON=D:\pytools\python.exe
    echo   - Or install the dependencies:
    echo       D:\pytools\python.exe -m pip install pygame pyinstaller
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%V in ('"!PY!" -V 2^>^&1') do echo [Python] !PY!  ^(%%V^)

REM ============================================================
REM  Clean previous output
REM ============================================================
echo [1/3] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MCTD.spec del /q MCTD.spec

REM ============================================================
REM  Build
REM ============================================================
echo [2/3] Building... (first build is slow, please wait)
REM  Derive the interpreter folder so conda's support DLLs can be located.
for %%D in ("!PY!") do set "PYDIR=%%~dpD"
if "!PYDIR:~-1!"=="\" set "PYDIR=!PYDIR:~0,-1!"

REM  Excluding numpy is important: Anaconda's numpy drags in ~500MB of MKL
REM  math libraries that this game never uses. Dropping it shrinks the exe a lot.
REM  Side effect: the stdlib extension DLLs it shares a folder with are no longer
REM  auto-collected, so add the few that are actually needed (total < 1MB).
set EXTRA=
for %%D in (libexpat.dll libbz2.dll liblzma.dll libmpdec-4.dll ffi.dll) do (
    if exist "!PYDIR!\Library\bin\%%D" set EXTRA=!EXTRA! --add-binary "!PYDIR!\Library\bin\%%D;."
)

"!PY!" -m PyInstaller --noconfirm --clean --onefile --noconsole --name MCTD ^
    !EXTRA! ^
    --exclude-module numpy ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module tkinter ^
    --add-data "bgm;bgm" ^
    --add-data "debuff;debuff" ^
    --add-data "enchantment;enchantment" ^
    --add-data "enemy;enemy" ^
    --add-data "fx;fx" ^
    --add-data "sound;sound" ^
    --add-data "tower;tower" ^
    --add-data "video;video" ^
    --add-data "Minecraft.ttf;." ^
    --add-data "seed.json;." ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check the log above.
    pause
    exit /b 1
)

if not exist "dist\MCTD.exe" (
    echo.
    echo [ERROR] dist\MCTD.exe was not created.
    pause
    exit /b 1
)

echo [3/3] Done
for %%F in ("dist\MCTD.exe") do echo     Output: %%~fF  (%%~zF bytes)
echo.
pause
exit /b 0

REM ============================================================
:check_python
REM  Return 0 if the given interpreter can import pygame and PyInstaller
REM ============================================================
if not exist "%~1" exit /b 1
"%~1" -c "import pygame, PyInstaller" >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0
