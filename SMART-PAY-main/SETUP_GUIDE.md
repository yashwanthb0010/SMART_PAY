# SMART-PAY Project - Setup & Installation Guide

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Requirements](#system-requirements)
3. [Dependencies](#dependencies)
4. [Installation Steps](#installation-steps)
5. [Running the Project](#running-the-project)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview
SMART-PAY is a Flask-based banking application with the following features:
- User registration and authentication
- Admin dashboard
- Money transfer and transactions
- Face recognition (optional)
- QR code generation
- User profiles and account management

---

## 💻 System Requirements
- **Python:** 3.8 or higher (3.11+ recommended)
- **MongoDB:** Running locally on `mongodb://localhost:27017/`
- **Operating System:** Windows 10/11 (Linux/Mac also supported)
- **RAM:** Minimum 4GB
- **Disk Space:** At least 500MB free

---

## 📦 Dependencies

### Python Packages Required:
```
flask==3.1.3              # Web framework
pymongo==4.17.0           # MongoDB driver
qrcode==8.2               # QR code generation
pillow==12.2.0            # Image processing
werkzeug==3.1.8           # WSGI utilities (Flask dependency)
jinja2==3.1.6             # Template engine
```

### Optional Dependencies:
```
face_recognition==1.3.0   # Face detection (requires dlib, may have installation issues)
dlib==20.0.1              # Machine learning library (optional)
```

### External Requirements:
```
MongoDB Community Edition (local database)
```

---

## 🚀 Installation Steps

### Step 1: Clone/Navigate to Project
```powershell
cd c:\Users\Yashwanth\Downloads\SMART-PAY-main\SMART-PAY-main
```

### Step 2: Create Virtual Environment (First Time Only)
```powershell
python -m venv .venv
```

### Step 3: Activate Virtual Environment
```powershell
.\.venv\Scripts\activate
```
You should see `(.venv)` in your terminal prompt.

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Setup Environment Variables
1. Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example -Destination .env
```

2. Edit `.env` file with your settings:
```
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=bank_demo
FACE_RECOGNITION_ENABLED=False
```

### Step 6: Verify Installation

**Optional:** To install face recognition (may require C++ build tools):
```powershell
pip install face_recognition
```

### Step 5: Verify Installation
```powershell
pip list
```

---

## 🏃 Running the Project

### Quick Start (One Command)
```powershell
cd SMART-PAY-main && .\.venv\Scripts\activate && python app.py
```

### Step-by-Step (Recommended for First Time)

**Step 1:** Open VS Code
- Open the project folder: `c:\Users\Yashwanth\Downloads\SMART-PAY-main`

**Step 2:** Open Terminal
- Press `CTRL + `` (backtick) in VS Code
- Or go to **Terminal** → **New Terminal**

**Step 3:** Navigate to Project
```powershell
cd SMART-PAY-main
```

**Step 4:** Activate Virtual Environment
```powershell
.\.venv\Scripts\activate
```

**Step 5:** Run Application
```powershell
python app.py
```

**Step 6:** Access the Application
- Open your browser and go to: `http://localhost:5000`
- Or: `http://127.0.0.1:5000`

---

## 📱 Application Features

Once running, you can access:

| Feature | URL | Description |
|---------|-----|-------------|
| Home | `http://localhost:5000/` | Landing page |
| Register | `http://localhost:5000/register` | User registration |
| Login | `http://localhost:5000/login` | User login |
| Admin Panel | `http://localhost:5000/admin` | Admin dashboard |
| User Dashboard | `http://localhost:5000/user` | User account dashboard |

---

## ⚙️ Configuration

### Environment Variables Setup
The project now uses `.env` file for configuration. Key variables:

```
FLASK_ENV              # development, production, or testing
FLASK_DEBUG            # True or False
SECRET_KEY             # Your Flask secret key
MONGO_URI              # MongoDB connection string
MONGO_DB_NAME          # Database name
FACE_RECOGNITION_ENABLED # True or False
```

### How to Setup:
1. Copy `.env.example` to `.env`
2. Update values in `.env` as needed
3. **Never commit `.env` to git** (only `.env.example`)

### MongoDB Setup
Make sure MongoDB is running locally:
```powershell
# Check if MongoDB is running
Get-Process mongod
```

### Flask Configuration Classes
The `config.py` file provides environment-specific settings:
- **DevelopmentConfig** - Debug mode enabled, relaxed security
- **ProductionConfig** - Debug disabled, enhanced security
- **TestingConfig** - For unit testing

---

## 🛑 Stopping the Server

Press `CTRL + C` in the terminal where the Flask app is running.

---

## 🔧 Troubleshooting

### Issue 1: "ModuleNotFoundError: No module named 'flask'"
**Solution:**
```powershell
pip install flask pymongo qrcode pillow
```

### Issue 2: Virtual Environment Not Activated
**Solution:**
```powershell
.\.venv\Scripts\activate
```

### Issue 3: Port 5000 Already in Use
**Solution:** Use a different port:
```powershell
$env:FLASK_PORT=5001
python app.py
```
Then access at: `http://localhost:5001`

### Issue 4: MongoDB Connection Error
**Solution:** Ensure MongoDB is running
```powershell
# Start MongoDB (if installed locally)
mongod
```

### Issue 5: Face Recognition Installation Fails
**Solution:** This is optional. The app works without it. Skip this package and proceed.

---

## 📝 Project Structure

```
SMART-PAY-main/
├── app.py                 # Main Flask application entry point
├── config.py              # Configuration settings (NEW)
├── requirements.txt       # Python dependencies (NEW)
├── .env.example           # Environment variables template (NEW)
├── .gitignore             # Git ignore file (NEW)
│
├── admin.py               # Admin blueprint/routes
├── user.py                # User blueprint/routes
├── face_utils.py          # Face recognition utilities
│
├── templates/             # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── admin/             # Admin templates
│   │   ├── dashboard.html
│   │   ├── user_details.html
│   │   ├── deposit.html
│   │   └── withdraw.html
│   └── user/              # User templates
│       ├── dashboard.html
│       ├── send_money.html
│       ├── transactions.html
│       └── ...
│
├── static/                # Static files (NEW)
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   ├── js/
│   │   └── script.js      # Main JavaScript file
│   ├── images/            # Images folder
│   └── uploads/           # User uploads (temp files)
│
├── utils/                 # Utility modules (NEW)
│   ├── __init__.py
│   ├── db.py              # Database helpers
│   └── helpers.py         # General helper functions
│
├── .venv/                 # Virtual environment
├── logs/                  # Application logs (NEW)
│
├── SETUP_GUIDE.md         # This setup guide
└── README.md              # Project README
```

---

## 🔄 Quick Reference Commands

| Command | Purpose |
|---------|---------|
| `cd SMART-PAY-main` | Navigate to project |
| `.\.venv\Scripts\activate` | Activate virtual environment |
| `python app.py` | Start Flask server |
| `pip install [package]` | Install Python package |
| `pip list` | List installed packages |
| `CTRL + C` | Stop Flask server |
| `deactivate` | Deactivate virtual environment |

---

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify all dependencies are installed: `pip list`
3. Ensure MongoDB is running
4. Check terminal output for error messages

---

## ✅ Verification Checklist

Before running the project, verify:
- [ ] Python 3.8+ installed
- [ ] Project folder exists
- [ ] Virtual environment created (`.venv` folder present)
- [ ] Dependencies installed (`pip list` shows flask, pymongo, etc.)
- [ ] MongoDB running (optional but recommended)
- [ ] Port 5000 is available

---

## 🎓 Next Steps

1. **First Time Setup:** Follow steps 1-6 in "Running the Project"
2. **Future Runs:** Just activate venv and run `python app.py`
3. **Development:** Make changes to files, Flask will auto-reload
4. **Deployment:** Use a production WSGI server (Gunicorn, etc.)

---

**Created:** June 27, 2026
**Last Updated:** June 27, 2026

---

## 🔄 Project Organization Updates (v1.1)

The project has been reorganized for better maintainability and production-readiness:

### ✅ New Files Added:
- **`requirements.txt`** - All Python dependencies in one file
- **`config.py`** - Centralized configuration management
- **`.env.example`** - Template for environment variables
- **`.gitignore`** - Git configuration file
- **`utils/db.py`** - Database connection utilities
- **`static/css/style.css`** - Main stylesheet
- **`static/js/script.js`** - Main JavaScript file

### 📁 New Directories:
- **`static/`** - For CSS, JavaScript, and images
- **`utils/`** - For helper functions and utilities
- **`logs/`** - For application logs (auto-created)

### 🎯 Benefits:
1. **Better Organization** - Code is organized by functionality
2. **Easier Maintenance** - Configuration separated from code
3. **Security** - Sensitive data in `.env` file (not in git)
4. **Scalability** - Utilities folder for reusable code
5. **Production-Ready** - Follows Flask best practices
6. **Version Control** - `.gitignore` prevents committing sensitive files
