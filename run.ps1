$ErrorActionPreference = 'Stop'

if (-Not (Test-Path .venv)) {
    Write-Host ".venv does not exist. Run .\setup_env.ps1 first." -ForegroundColor Yellow
    exit 1
}

Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host "Starting Flask app..."
python app.py
