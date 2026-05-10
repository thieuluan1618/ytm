@echo off
REM One-shot setup for YTM CLI on Windows Command Prompt
REM Creates venv, installs dependencies, and configures the `ytm` command.

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo YTM CLI Setup
echo =============
echo.

REM 1. Check Python (>= 3.14)
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.14+ from https://python.org
    exit /b 1
)
for /f "delims=" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do set "PY_VERSION=%%v"
if not defined PY_VERSION (
    echo [ERROR] Failed to query Python version
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.14+ required, found %PY_VERSION%
    exit /b 1
)
echo [OK] Python %PY_VERSION% detected

REM 2. Check / install mpv
where mpv >nul 2>&1
if errorlevel 1 (
    echo [WARN] mpv not found
    where winget >nul 2>&1
    if errorlevel 1 (
        echo        winget not available. Install mpv from https://mpv.io/installation/
    ) else (
        set /p MPV_ANSWER="       Install mpv via winget now? (y/n) "
        if /i "!MPV_ANSWER!"=="y" (
            winget install --id mpv.net -e --accept-source-agreements --accept-package-agreements
            where mpv >nul 2>&1
            if errorlevel 1 (
                echo [WARN] mpv install didn't register in PATH. Open a new terminal after setup completes.
            ) else (
                echo [OK] mpv installed
            )
        ) else (
            echo        Skipping mpv install - ytm playback won't work until it's installed.
        )
    )
) else (
    echo [OK] mpv detected
)
echo.

REM 3. Create venv
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        exit /b 1
    )
) else (
    echo Virtual environment already exists
)

REM 4. Install dependencies
echo Installing dependencies...
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    exit /b 1
)
python -m pip install --quiet --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    exit /b 1
)
python -m pip install --quiet .
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies from pyproject.toml
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM 5. Configure alias
echo Configuring 'ytm' command...
call "%SCRIPT_DIR%setup_alias.bat"
if errorlevel 1 (
    echo [ERROR] Alias setup failed. You can run setup_alias.bat manually later.
    exit /b 1
)

echo.
echo Setup complete! Open a new terminal and run:  ytm
endlocal
