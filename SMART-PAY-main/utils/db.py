"""
Database utility functions for MongoDB connections
"""
from pymongo import MongoClient
from config import app_config


def get_db_connection():
    """
    Get MongoDB database connection
    
    Returns:
        Database object from MongoDB
    """
    client = MongoClient(app_config.MONGO_URI)
    db = client[app_config.MONGO_DB_NAME]
    return db


def get_users_collection():
    """Get users collection from database"""
    db = get_db_connection()
    return db['users']


def get_transactions_collection():
    """Get transactions collection from database"""
    db = get_db_connection()
    return db['transactions']


def get_vaults_collection():
    """Get vaults collection from database"""
    db = get_db_connection()
    return db['vaults']
