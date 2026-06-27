$ErrorActionPreference = 'Stop'

Write-Host "Creating virtual environment .venv..."
py -3.11 -m venv .venv

Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing base requirements..."
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

Write-Host "Installing optional face recognition dependencies..."
python -m pip install face_recognition opencv-python

Write-Host "Setup complete. Use run.ps1 to start the app."
