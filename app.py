"""
Главный Flask application
"""
import logging
import os
import sys

# Добавляем текущую директорию в Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from config import LOGGING_CONFIG, SECRET_KEY, MAX_CONTENT_LENGTH

# Настройка логирования ПЕРЕД импортом Flask
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def create_app():
    """Создание Flask приложения"""
    from flask import Flask
    from web.routes import configure_routes
    from web.utils import cleanup_old_sessions

    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

    # Настройка маршрутов
    configure_routes(app)

    # Очистка старых сессий при старте
    cleanup_old_sessions()

    logger.info("✅ Business Card Prepress application initialized")

    return app