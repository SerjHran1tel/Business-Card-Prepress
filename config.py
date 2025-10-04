"""
Конфигурационные настройки приложения
"""
import os
from pathlib import Path

# Базовые пути - учитываем Docker окружение
if os.path.exists('/app'):
    # Docker окружение
    BASE_DIR = Path('/app')
else:
    # Локальное окружение
    BASE_DIR = Path(__file__).parent

UPLOAD_FOLDER = BASE_DIR / 'uploads'
OUTPUT_FOLDER = BASE_DIR / 'output'
LOG_FOLDER = BASE_DIR / 'logs'

# Создаем директории
UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)
LOG_FOLDER.mkdir(exist_ok=True, parents=True)

# Настройки приложения
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

# Поддерживаемые форматы
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'eps'}

# ПРОСТАЯ настройка логирования для basicConfig
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'datefmt': '%Y-%m-%d %H:%M:%S'
}

# Проверка зависимостей
try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import fitz  # PyMuPDF
    PYPDF2_SUPPORT = True
except ImportError:
    PYPDF2_SUPPORT = False