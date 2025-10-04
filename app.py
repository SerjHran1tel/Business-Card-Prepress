"""
Главный Flask application
"""
import logging

from flask import Flask

from config import LOGGING_CONFIG, SECRET_KEY, MAX_CONTENT_LENGTH
from web.routes import configure_routes
from web.utils import cleanup_old_sessions

# Настройка логирования
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def create_app():
    """Создание Flask приложения"""
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

    # Настройка маршрутов
    configure_routes(app)

    # Очистка старых сессий при старте
    cleanup_old_sessions()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)