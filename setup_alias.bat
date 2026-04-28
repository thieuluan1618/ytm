@echo off
REM Setup script for Windows Command Prompt
REM Creates ytm.bat wrapper in a directory on PATH
REM Uses uv for dependency management (falls back to venv if uv not available)

setlocal EnableDelayedExpansion

echo.
echo === YTM CLI Setup for Windows Command Prompt ===
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Check if uv is available
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Found uv — using uv run for wrapper
    echo.
    set USE_UV=1
) else (
    echo [WARNING] uv not found — falling back to venv
    echo    Install uv for a better experience: https://docs.astral.sh/uv/
    echo.
    set USE_UV=0
    set VENV_PATH=%SCRIPT_DIR%\venv

    if not exist "!VENV_PATH!" (
        echo [ERROR] Virtual environment not found at: !VENV_PATH!
        echo.
        echo Please install uv or create a venv:
        echo   pip install uv
        echo   REM or
        echo   python -m venv venv
        echo   venv\Scripts\activate.bat
        echo   pip install -r requirements.txt
        exit /b 1
    )
)

REM Find a suitable directory on PATH to place the wrapper
set TARGET_DIR=
for %%d in ("%USERPROFILE%\bin" "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps") do (
    if exist "%%~d" (
        set TARGET_DIR=%%~d
        goto :found_dir
    )
)

REM Create %USERPROFILE%\bin if nothing suitable found
set TARGET_DIR=%USERPROFILE%\bin
if not exist "%TARGET_DIR%" (
    echo Creating directory: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
)

:found_dir
echo Found target directory: %TARGET_DIR%
echo.

REM Create the wrapper batch file
set WRAPPER_FILE=%TARGET_DIR%\ytm.bat
echo Creating wrapper: %WRAPPER_FILE%

if %USE_UV% equ 1 (
    (
        echo @echo off
        echo REM YTM CLI - YouTube Music CLI Tool
        echo uv run --project "%SCRIPT_DIR%" ytm-cli %%*
    ) > "%WRAPPER_FILE%"
) else (
    (
        echo @echo off
        echo REM YTM CLI - YouTube Music CLI Tool
        echo cd /d "%SCRIPT_DIR%"
        echo call "%VENV_PATH%\Scripts\activate.bat"
        echo python -m ytm_cli %%*
    ) > "%WRAPPER_FILE%"
)

REM Check if target directory is in PATH
echo %PATH% | findstr /C:"%TARGET_DIR%" >nul
if errorlevel 1 (
    echo.
    echo [WARNING] %TARGET_DIR% is NOT in your PATH
    echo.
    echo To add it permanently, run:
    echo   setx PATH "%%PATH%%;%TARGET_DIR%"
    echo.
    echo Or add it manually via:
    echo   System Properties ^> Environment Variables ^> User Variables ^> PATH
    echo.
    echo For this session only, run:
    echo   set PATH=%%PATH%%;%TARGET_DIR%
) else (
    echo.
    echo [SUCCESS] Successfully created 'ytm' command!
    echo.
    echo You can now use: ytm [search query]
)

echo.
pause
