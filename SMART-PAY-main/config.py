"""
Configuration module for SMART-PAY application
Handles all environment-based settings and configurations
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class with common settings"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'REPLACE_WITH_A_STRONG_SECRET_IN_PRODUCTION')
    DEBUG = os.getenv('DEBUG', False)
    TESTING = False
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'bank_demo')
    
    # Application Settings
    APP_NAME = 'SMART-PAY'
    APP_VERSION = '1.0.0'
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    
    # Face Recognition Settings
    FACE_RECOGNITION_ENABLED = os.getenv('FACE_RECOGNITION_ENABLED', 'False').lower() == 'true'
    

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False
    

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    

class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    DEBUG = True
    MONGO_DB_NAME = 'bank_demo_test'
    

# Select configuration based on environment
config_env = os.getenv('FLASK_ENV', 'development').lower()

if config_env == 'production':
    app_config = ProductionConfig()
elif config_env == 'testing':
    app_config = TestingConfig()
else:
    app_config = DevelopmentConfig()
