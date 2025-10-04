"""
Главный класс приложения для импозиции
"""
import json
import logging
from typing import List, Optional
from pathlib import Path

from .models import PageFormat, CardSize, MatchingMode, ColorMode, PrintSettings, CardQuantity
from .pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)


class ImpositionApp:
    def __init__(self):
        self.settings = PrintSettings(
            page_format=PageFormat.get_standard_formats()['A4'],
            card_size=CardSize.get_standard_sizes()['Standard RU']
        )
        self.logger = logging.getLogger(__name__)

    def process(self, front_cards: List[CardQuantity],
                back_cards: Optional[List[CardQuantity]],
                output_file: str) -> bool:
        self.logger.info(f"Начало обработки, выходной файл: {output_file}")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generator = PDFGenerator(self.settings)
        success = generator.create_imposition(front_cards, back_cards, output_path)

        if success:
            self.logger.info(f"✅ PDF успешно создан: {output_path}")
        else:
            self.logger.error("❌ Ошибка при создании PDF")

        return success

    def save_config(self, config_file: str):
        config = {
            'page_format': {
                'name': self.settings.page_format.name,
                'width': self.settings.page_format.width,
                'height': self.settings.page_format.height
            },
            'card_size': {
                'width': self.settings.card_size.width,
                'height': self.settings.card_size.height
            },
            'margins': {
                'top': self.settings.margin_top,
                'bottom': self.settings.margin_bottom,
                'left': self.settings.margin_left,
                'right': self.settings.margin_right
            },
            'bleed': self.settings.bleed,
            'gap': self.settings.gap,
            'crop_marks': self.settings.crop_marks,
            'dpi': self.settings.dpi,
            'output_dpi': self.settings.output_dpi,
            'color_mode': self.settings.color_mode.value,
            'matching_mode': self.settings.matching_mode.value,
            'strict_name_matching': self.settings.strict_name_matching
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Конфигурация сохранена: {config_file}")

    def load_config(self, config_file: str):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.settings.page_format = PageFormat(**config['page_format'])
        self.settings.card_size = CardSize(**config['card_size'])
        self.settings.margin_top = config['margins']['top']
        self.settings.margin_bottom = config['margins']['bottom']
        self.settings.margin_left = config['margins']['left']
        self.settings.margin_right = config['margins']['right']
        self.settings.bleed = config['bleed']
        self.settings.gap = config['gap']
        self.settings.crop_marks = config['crop_marks']
        self.settings.dpi = config.get('dpi', 300)
        self.settings.output_dpi = config.get('output_dpi', 300)
        self.settings.color_mode = ColorMode(config.get('color_mode', 'rgb'))
        self.settings.matching_mode = MatchingMode(config['matching_mode'])
        self.settings.strict_name_matching = config.get('strict_name_matching', True)

        self.logger.info(f"Конфигурация загружена: {config_file}")