# One-shot setup for YTM CLI on Windows PowerShell
# Creates venv, installs dependencies, and configures the `ytm` function.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "YTM CLI Setup" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python (>= 3.14)
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found. Please install Python 3.14+ from https://python.org" -ForegroundColor Red
    exit 1
}
$pyVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to query Python version" -ForegroundColor Red
    exit 1
}
& python -c "import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.14+ required, found $pyVersion" -ForegroundColor Red
    exit 1
}
Write-Host "Python $pyVersion detected" -ForegroundColor Green

# 2. Check / install mpv
$mpv = Get-Command mpv -ErrorAction SilentlyContinue
if ($mpv) {
    Write-Host "mpv detected" -ForegroundColor Green
} else {
    Write-Host "mpv not found" -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        $answer = Read-Host "   Install mpv via winget now? (y/n)"
        if ($answer -match '^[Yy]') {
            & winget install --id mpv.net -e --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) {
                Write-Host "winget install failed. Install mpv manually from https://mpv.io/installation/" -ForegroundColor Red
                exit 1
            }
            $mpv = Get-Command mpv -ErrorAction SilentlyContinue
            if (-not $mpv) {
                Write-Host "mpv installed but not yet in PATH. Open a new terminal after setup completes." -ForegroundColor Yellow
            } else {
                Write-Host "mpv installed" -ForegroundColor Green
            }
        } else {
            Write-Host "   Skipping mpv install - ytm playback won't work until it's installed." -ForegroundColor Yellow
        }
    } else {
        Write-Host "   winget not available. Install mpv manually from https://mpv.io/installation/" -ForegroundColor Yellow
    }
}
Write-Host ""

# 3. Create venv
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Virtual environment already exists"
}

$VenvPython = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment python not found at $VenvPython" -ForegroundColor Red
    exit 1
}

# 4. Install dependencies
Write-Host "Installing dependencies..."
& $VenvPython -m pip install --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upgrade pip" -ForegroundColor Red
    exit 1
}
& $VenvPython -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies from requirements.txt" -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies installed" -ForegroundColor Green
Write-Host ""

# 5. Configure PowerShell function
Write-Host "Configuring 'ytm' function..."
& "$ScriptDir\setup_alias.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Alias setup failed. You can run setup_alias.ps1 manually later." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup complete! Reload your profile (. `$PROFILE) and run:  ytm" -ForegroundColor Green
