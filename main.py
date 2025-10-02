# -*- coding: utf-8 -*-
# main.py
import sys
import os
import atexit
import tempfile
import shutil
import tkinter as tk
from gui.main_window import MainWindow

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Глобальная временная папка для конвертированных файлов
TEMP_CONVERT_DIR = None
app_instance = None


def setup_temp_dir():
    """Создание временной папки для логов и других временных данных"""
    global TEMP_CONVERT_DIR
    TEMP_CONVERT_DIR = tempfile.mkdtemp(prefix="prepress_app_")
    return TEMP_CONVERT_DIR


def cleanup_temp_files():
    """Очистка временных файлов при выходе"""
    # Очистка папки логов
    global TEMP_CONVERT_DIR
    if TEMP_CONVERT_DIR and os.path.exists(TEMP_CONVERT_DIR):
        try:
            shutil.rmtree(TEMP_CONVERT_DIR)
            print(f"Очищена временная папка: {TEMP_CONVERT_DIR}")
        except Exception as e:
            print(f"Ошибка очистки временной папки: {e}")

    # Очистка временных файлов, созданных конвертером
    if app_instance and hasattr(app_instance, 'temp_files'):
        cleaned_count = 0
        # Очищаем также временные файлы из партий
        all_temp_files = set(app_instance.temp_files)
        for party in app_instance.parties:
            for f in party.front_images + party.back_images:
                if 'tmp' in f or 'temp' in f:
                    all_temp_files.add(f)

        for f in all_temp_files:
            try:
                if os.path.exists(f):
                    os.unlink(f)
                    cleaned_count += 1
            except Exception as e:
                print(f"Не удалось удалить временный файл {f}: {e}")
        if cleaned_count > 0:
            print(f"Очищено {cleaned_count} временных файлов конвертации.")


def main():
    """Главная функция приложения"""
    global app_instance
    try:
        # Создаем временную папку
        temp_dir = setup_temp_dir()

        # Регистрируем очистку при выходе
        atexit.register(cleanup_temp_files)

        # Настройка логирования - ИСПРАВЛЕННАЯ СТРОКА
        from utils.logger import setup_logging
        setup_logging(log_dir=temp_dir)  # Теперь функция принимает log_dir

        print("Запуск графического интерфейса...")
        print("Поддерживаемые форматы: JPG, PNG, TIFF, BMP, WEBP, PDF, EPS, SVG")

        root = tk.Tk()
        app_instance = MainWindow(root)
        root.mainloop()

    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что установлены все зависимости:")
        print("pip install -r requirements.txt")
        input("Нажмите Enter для выхода...")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()