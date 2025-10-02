# -*- coding: utf-8 -*-
# utils/logger.py
import logging
import os
import sys
from datetime import datetime


def setup_logging(log_dir=None, level=logging.INFO):
    """
    Настройка системы логирования
    """
    # Создаем логгер
    logger = logging.getLogger()
    logger.setLevel(level)

    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Обработчик для файла (если указана директория)
    if log_dir and os.path.exists(log_dir):
        log_file = os.path.join(log_dir, f"prepress_app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Логирование в файл: {log_file}")

    logger.info("Система логирования инициализирована")
    return logger