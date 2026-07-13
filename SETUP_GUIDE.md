# Quick Setup Guide - SMART-PAY

Follow these 4 simple steps to run the project immediately.

### Prerequisites
- **Python 3.8+** installed.
- **MongoDB** running locally (`mongodb://localhost:27017/`).

---

### Step 1: Open Terminal in the Project Folder
Open your terminal (PowerShell or Command Prompt) inside the `SMART-PAY-main` folder.

### Step 2: Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```
*(On Mac/Linux, use `source .venv/bin/activate` instead)*

### Step 3: Install Requirements & Setup Environment
```powershell
pip install -r requirements.txt
Copy-Item .env.example -Destination .env
```
*(On Mac/Linux, use `cp .env.example .env` instead)*

### Step 4: Run the App
```powershell
python app.py
```

Done! 🎉 Open your browser to **http://127.0.0.1:5000** to use the app.
