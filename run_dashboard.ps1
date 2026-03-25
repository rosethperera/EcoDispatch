$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".env.local") -and -not (Test-Path ".env")) {
    Write-Host "Missing .env.local or .env file." -ForegroundColor Yellow
    Write-Host "Copy .env.example to .env.local and add your real Electricity Maps token." -ForegroundColor Yellow
    exit 1
}

streamlit run dashboard.py
