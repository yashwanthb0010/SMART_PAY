# SMART-PAY

A Flask banking demo with optional face recognition.

## Setup

### Requirements
- Windows
- Python 3.11 installed
- `py` launcher available
- Git installed (for optional face recognition models)
- (optional) Visual Studio Build Tools with C++ support for `dlib` if face recognition extras must be compiled

### One-time setup
Open PowerShell in the project root and run:

```powershell
.\setup_env.ps1
```

This will:
- create `.venv`
- install base dependencies from `requirements.txt`
- attempt to install optional face recognition packages

### Run the app
In PowerShell:

```powershell
.\run.ps1
```

### Optional face recognition installation
If the setup script could not install face recognition extras automatically, run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-face.txt
```

### VS Code setup
If you use VS Code, the project includes `.vscode/settings.json` to automatically use the local `.venv` interpreter.

Open the folder in VS Code and select the interpreter at:

```text
.venv\Scripts\python.exe
```

### Important
Always use the project virtual environment before running the app:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

### Troubleshooting
- If `py -3.11` is not found, install Python 3.11 and enable the Python launcher.
- If face recognition install fails, install Visual Studio Build Tools with C++ support.
- Do not install project dependencies globally for this repo.
