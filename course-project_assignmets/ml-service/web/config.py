"""Конфигурация Web-приложения из переменных окружения."""

import os


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change_me_in_production")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://app:8000")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
