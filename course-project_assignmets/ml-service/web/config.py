"""Конфигурация Web-приложения из переменных окружения."""

import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    API_URL = os.getenv("API_URL", "http://localhost:8000")
