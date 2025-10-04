"""
Точка входа для запуска приложения
"""
import os
import sys

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    from app import create_app

    app = create_app()

    # Получаем хост и порт из переменных окружения
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))

    print(f"🚀 Запуск Business Card Prepress на {host}:{port}")
    print(f"📁 Рабочая директория: {os.getcwd()}")

    app.run(host=host, port=port, debug=False)