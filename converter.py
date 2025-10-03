# -*- coding: utf-8 -*-
# converter.py
import fitz  # PyMuPDF
import os
import tempfile
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Только форматы, которые можно конвертировать через Python библиотеки
SUPPORTED_VECTOR_FORMATS = ('.pdf', '.svg')  # Убрали EPS, AI, CDR, WMF, EMF


def convert_to_raster(filepath, dpi=300):
    """
    Конвертирует векторный файл во временный растровый PNG.
    Если формат не векторный, возвращает исходный путь.
    """
    if not filepath.lower().endswith(SUPPORTED_VECTOR_FORMATS):
        return filepath, None

    try:
        file_ext = os.path.splitext(filepath.lower())[1]

        # Создаем временный файл для сконвертированного изображения
        temp_fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)

        success = False
        error_message = None

        if file_ext == '.pdf':
            success, error_message = _convert_pdf(filepath, temp_path, dpi)
        elif file_ext == '.svg':
            success, error_message = _convert_svg(filepath, temp_path, dpi)

        if success:
            logger.info(f"Файл '{os.path.basename(filepath)}' успешно конвертирован в '{temp_path}'")
            return temp_path, None
        else:
            # Удаляем временный файл в случае ошибки
            try:
                os.unlink(temp_path)
            except:
                pass
            return filepath, error_message

    except Exception as e:
        error_message = f"Ошибка конвертации файла {os.path.basename(filepath)}: {e}"
        logger.error(error_message)
        return filepath, error_message


def _convert_pdf(filepath, output_path, dpi):
    """Конвертировать PDF в PNG через PyMuPDF"""
    try:
        doc = fitz.open(filepath)
        page = doc.load_page(0)  # Загружаем первую страницу

        # Рендерим страницу в PNG с высоким разрешением
        pix = page.get_pixmap(dpi=dpi)
        pix.save(output_path)
        doc.close()
        return True, None
    except Exception as e:
        return False, f"Ошибка конвертации PDF: {e}"


def _convert_svg(filepath, output_path, dpi):
    """Конвертировать SVG в PNG через CairoSVG"""
    try:
        import cairosvg
        cairosvg.svg2png(url=filepath, write_to=output_path, dpi=dpi)
        if os.path.exists(output_path):
            return True, None
        else:
            return False, "CairoSVG не создал выходной файл"
    except ImportError:
        return False, "Для конвертации SVG установите: pip install cairosvg"
    except Exception as e:
        return False, f"Ошибка конвертации SVG: {e}"


def check_conversion_dependencies():
    """Проверить доступные Python библиотеки для конвертации"""
    missing_tools = []

    # Проверяем CairoSVG для SVG
    try:
        import cairosvg
    except ImportError:
        missing_tools.append("CairoSVG (для SVG файлов) - pip install cairosvg")

    # PyMuPDF уже должен быть установлен для PDF

    return missing_tools