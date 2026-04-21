"""
Конфигурация приложения через переменные окружения (pydantic-settings).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # База данных
    db_host: str = "database"
    db_port: int = 5432
    db_name: str = "ml_service"
    db_user: str = "postgres"
    db_password: str = "postgres"

    # JWT
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_PLEASE"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 часа

    # RabbitMQ
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_queue: str = "ml_tasks"

    # Приложение
    debug: bool = False
    app_title: str = "ML Service API"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
