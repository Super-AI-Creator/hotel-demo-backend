import os
from datetime import timedelta


class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    JSON_SORT_KEYS = False

    # Database (MySQL via PyMySQL)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'ttlock')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # PMS (Beds24 defaults - per-hotel overrides live in DB)
    BEDS24_BASE_URL = os.getenv('BEDS24_BASE_URL', 'https://api.beds24.com/v2')

    # TTLock (per-hotel credentials live in DB)
    TTLOCK_BASE_URL = os.getenv('TTLOCK_BASE_URL', 'https://euapi.ttlock.com')