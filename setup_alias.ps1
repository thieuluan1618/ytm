# PowerShell setup script for Windows
# Creates 'ytm' function in PowerShell profile

$ErrorActionPreference = "Stop"

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $ScriptDir "venv"
$VenvActivate = Join-Path $VenvPath "Scripts\Activate.ps1"

Write-Host "🔍 YTM CLI Setup for PowerShell" -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path $VenvPath)) {
    Write-Host "❌ Virtual environment not found at: $VenvPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv"
    Write-Host "  .\venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

# Check if PowerShell profile exists
if (-not (Test-Path $PROFILE)) {
    Write-Host "📝 Creating PowerShell profile at: $PROFILE" -ForegroundColor Yellow
    New-Item -Path $PROFILE -Type File -Force | Out-Null
}

# Define the function
$FunctionCode = @"

# YTM CLI - YouTube Music CLI Tool
function ytm {
    Push-Location '$ScriptDir'
    & '$VenvActivate'
    python -m ytm_cli `$args
    Pop-Location
}
"@

# Check if function already exists
$ProfileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($ProfileContent -match "function ytm") {
    Write-Host "✅ 'ytm' function already exists in profile" -ForegroundColor Green
    Write-Host ""
    $Response = Read-Host "Do you want to update it? (Y/N)"
    if ($Response -ne "Y" -and $Response -ne "y") {
        Write-Host "Skipping update." -ForegroundColor Yellow
        exit 0
    }
    # Remove old function
    $ProfileContent = $ProfileContent -replace "(?ms)# YTM CLI.*?^}", ""
    Set-Content -Path $PROFILE -Value $ProfileContent.Trim()
}

# Add the function
Add-Content -Path $PROFILE -Value $FunctionCode

Write-Host "✅ Successfully added 'ytm' function to PowerShell profile" -ForegroundColor Green
Write-Host ""
Write-Host "To use immediately, run:" -ForegroundColor Cyan
Write-Host "  . `$PROFILE" -ForegroundColor White
Write-Host ""
Write-Host "Or simply restart PowerShell." -ForegroundColor Cyan
Write-Host ""
Write-Host "Then use: ytm [search query]" -ForegroundColor White
Write-Host ""
