# -*- coding: utf-8 -*-
# core/config.py
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Стандартные размеры листов (ширина × высота в мм)
SHEET_SIZES = {
    'A3': (297, 420),
    'A4': (210, 297),
    'A5': (148, 210),
    'SRA3': (305, 457),
    'Letter': (216, 279),
    'Legal': (216, 356),
    'Произвольный': None
}

# Стандартные размеры визиток (ширина × высота в мм)
CARD_SIZES = {
    'Стандартная (90×50)': (90, 50),
    'Евро (85×55)': (85, 55),
    'Квадратная (90×90)': (90, 90),
    'Мини (70×40)': (70, 40),
    'Произвольный': None
}

@dataclass
class PrintConfig:
    sheet_size: str = 'A4'
    custom_sheet: bool = False
    custom_sheet_width: int = 210
    custom_sheet_height: int = 297
    card_size: str = 'Стандартная (90×50)'
    custom_card_width: int = 90
    custom_card_height: int = 50
    margin: int = 5
    bleed: int = 3
    gutter: int = 2
    rotate_cards: bool = False
    add_crop_marks: bool = True
    mark_length: int = 5
    mark_thickness: float = 0.3
    matching_scheme: str = '1:1'
    fit_proportions: bool = True
    match_by_name: bool = False
    dpi: int = 300

    def get_sheet_dimensions(self) -> Tuple[int, int]:
        try:
            if self.custom_sheet:
                return (self.custom_sheet_width, self.custom_sheet_height)
            result = SHEET_SIZES.get(self.sheet_size, (210, 297))
            logger.debug(f"Sheet dimensions: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting sheet dimensions: {e}")
            return (210, 297)

    def get_card_dimensions(self) -> Tuple[int, int]:
        try:
            if self.card_size == 'Произвольный':
                return (self.custom_card_width, self.custom_card_height)
            result = CARD_SIZES.get(self.card_size, (90, 50))
            logger.debug(f"Card dimensions: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting card dimensions: {e}")
            return (90, 50)

@dataclass
class AppConfig:
    app_name: str = "Business Card Maker"
    version: str = "2.0.0"
    debug: bool = True
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp', '.pdf', '.svg'
    ])
    temp_dir: str = "temp"
    supported_vector_formats: List[str] = field(default_factory=lambda: ['.pdf', '.svg'])
    session_timeout: int = 3600  # 1 hour