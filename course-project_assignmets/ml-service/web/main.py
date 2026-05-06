"""
Точка входа Flask-приложения.
Регистрирует blueprints и запускает сервер.
"""

from flask import Flask
from config import Config
from routers.public import bp as public_bp
from routers.auth import bp as auth_bp
from routers.dashboard import bp as dashboard_bp


def create_app() -> Flask:
    app = Flask(__name__,
                template_folder="templates",
                static_folder="static")
    app.config.from_object(Config)

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
