# -*- coding: utf-8 -*-
# utils/logger.py
import logging
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs"):
    """Настройка логирования"""
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"business_card_maker_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Уменьшаем логирование для некоторых библиотек
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('reportlab').setLevel(logging.WARNING)
    logging.getLogger('fontTools').setLevel(logging.WARNING)

    return logging.getLogger(__name__)