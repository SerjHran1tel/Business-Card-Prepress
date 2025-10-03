# utils/helpers.py
import os
import logging

logger = logging.getLogger(__name__)

def ensure_directory(directory: str):
    """Создание директории если не существует"""
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Directory ensured: {directory}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")

def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def format_file_size(bytes_size: int) -> str:
    """Форматирование размера файла"""
    if bytes_size == 0:
        return '0 B'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"