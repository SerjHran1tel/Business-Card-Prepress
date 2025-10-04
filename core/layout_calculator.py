"""
Расчет раскладки визиток на листе
"""
import logging
from typing import Tuple

from .models import PrintSettings

logger = logging.getLogger(__name__)


class LayoutCalculator:
    @staticmethod
    def calculate_layout(settings: PrintSettings) -> Tuple[int, int, float, float]:
        available_width = (settings.page_format.width -
                          settings.margin_left - settings.margin_right)
        available_height = (settings.page_format.height -
                           settings.margin_top - settings.margin_bottom)

        card_width = settings.card_size.width + settings.gap
        card_height = settings.card_size.height + settings.gap

        cols = int(available_width // card_width)
        rows = int(available_height // card_height)

        cols = max(1, cols)
        rows = max(1, rows)

        total_cards_width = cols * card_width - settings.gap
        total_cards_height = rows * card_height - settings.gap

        x_offset = settings.margin_left + (available_width - total_cards_width) / 2
        y_offset = settings.margin_bottom + (available_height - total_cards_height) / 2

        logger.info(f"Раскладка: {cols}x{rows} визиток, offset: ({x_offset:.1f}, {y_offset:.1f})")
        return cols, rows, x_offset, y_offset

    @staticmethod
    def get_preview_data(settings: PrintSettings) -> dict:
        cols, rows, x_offset, y_offset = LayoutCalculator.calculate_layout(settings)

        return {
            'cols': cols,
            'rows': rows,
            'cards_per_sheet': cols * rows,
            'card_width': settings.card_size.width,
            'card_height': settings.card_size.height,
            'page_width': settings.page_format.width,
            'page_height': settings.page_format.height,
            'x_offset': x_offset,
            'y_offset': y_offset,
            'gap': settings.gap
        }