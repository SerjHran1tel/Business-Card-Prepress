# -*- coding: utf-8 -*-
# converter.py
import fitz  # PyMuPDF
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
SUPPORTED_VECTOR_FORMATS = ('.pdf', '.eps', '.ai')

def convert_to_raster(filepath, dpi=300):
    """
    Конвертирует векторный файл (PDF, EPS) во временный растровый PNG.
    Если формат не векторный, возвращает исходный путь.
    """
    if not filepath.lower().endswith(SUPPORTED_VECTOR_FORMATS):
        return filepath, None  # Возвращаем исходный путь, ошибок нет

    try:
        # Создаем временный файл для сконвертированного изображения
        temp_fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)

        doc = fitz.open(filepath)
        page = doc.load_page(0)  # Загружаем первую страницу

        # Рендерим страницу в PNG с высоким разрешением
        pix = page.get_pixmap(dpi=dpi)
        pix.save(temp_path)
        doc.close()

        logger.info(f"Файл '{os.path.basename(filepath)}' успешно конвертирован в '{temp_path}'")
        return temp_path, None # Возвращаем путь к временному файлу

    except Exception as e:
        error_message = f"Ошибка конвертации файла {os.path.basename(filepath)}: {e}"
        logger.error(error_message)
        return filepath, error_message # Возвращаем исходный путь и ошибку