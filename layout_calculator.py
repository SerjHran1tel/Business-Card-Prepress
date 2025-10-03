# -*- coding: utf-8 -*-
# layout_calculator.py
import logging
from core.models import LayoutResult

logger = logging.getLogger(__name__)

class LayoutCalculator:
    def __init__(self, sheet_width, sheet_height, card_width, card_height,
                 margin, bleed, gutter, rotate=False):
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height
        self.card_width = card_width
        self.card_height = card_height
        self.margin = margin
        self.bleed = bleed
        self.gutter = gutter
        self.rotate = rotate

        logger.info(f"LayoutCalculator init: sheet={sheet_width}x{sheet_height}, "
                    f"card={card_width}x{card_height}, margin={margin}, "
                    f"bleed={bleed}, gutter={gutter}, rotate={rotate}")

        self.work_width = sheet_width - 2 * margin
        self.work_height = sheet_height - 2 * margin

    def calculate_layout(self) -> LayoutResult:
        """Рассчитать оптимальную раскладку"""
        logger.info("Calculating layout...")

        layouts = []

        # Без поворота
        normal_layout = self._calculate_single_layout(False)
        if normal_layout['cards_total'] > 0:
            layouts.append(normal_layout)

        # С поворотом
        if self.rotate:
            rotated_layout = self._calculate_single_layout(True)
            if rotated_layout['cards_total'] > 0:
                layouts.append(rotated_layout)

        if not layouts:
            logger.warning("No valid layouts found")
            return self._get_empty_layout()

        best_layout = max(layouts, key=lambda x: x['cards_total'])
        logger.info(f"Best layout: {best_layout['cards_x']}x{best_layout['cards_y']} "
                    f"({best_layout['cards_total']} cards), rotated: {best_layout['rotated']}")

        return LayoutResult(**best_layout)

    def _calculate_single_layout(self, rotated):
        """Рассчитать раскладку для одного варианта"""
        try:
            if rotated:
                card_w, card_h = self.card_height, self.card_width
            else:
                card_w, card_h = self.card_width, self.card_height

            # Effective размер с bleed и gutter
            effective_w = card_w + 2 * self.bleed + self.gutter
            effective_h = card_h + 2 * self.bleed + self.gutter

            if self.work_width < card_w + 2 * self.bleed or self.work_height < card_h + 2 * self.bleed:
                logger.warning(
                    f"Card too large for work area: {card_w}x{card_h} vs {self.work_width}x{self.work_height}")
                return self._get_empty_layout()

            cards_x = int((self.work_width + self.gutter) // effective_w)
            cards_y = int((self.work_height + self.gutter) // effective_h)

            if cards_x == 0 or cards_y == 0:
                logger.warning(f"No cards fit: cards_x={cards_x}, cards_y={cards_y}")
                return self._get_empty_layout()

            total_width = cards_x * (card_w + 2 * self.bleed) + (cards_x - 1) * self.gutter
            total_height = cards_y * (card_h + 2 * self.bleed) + (cards_y - 1) * self.gutter

            offset_x = self.margin + (self.work_width - total_width) / 2
            offset_y = self.margin + (self.work_height - total_height) / 2

            positions = []
            for y in range(cards_y):
                for x in range(cards_x):
                    pos_x = offset_x + x * (card_w + 2 * self.bleed + self.gutter) - self.bleed
                    pos_y = offset_y + y * (card_h + 2 * self.bleed + self.gutter) - self.bleed
                    positions.append({
                        'x': pos_x,
                        'y': pos_y,
                        'width': card_w + 2 * self.bleed,
                        'height': card_h + 2 * self.bleed,
                        'rotated': rotated
                    })

            result = {
                'cards_x': cards_x,
                'cards_y': cards_y,
                'cards_total': cards_x * cards_y,
                'positions': positions,
                'rotated': rotated,
                'efficiency': (cards_x * card_w * cards_y * card_h) / (self.sheet_width * self.sheet_height)
            }

            logger.debug(f"Layout calculated: {result}")
            return result

        except Exception as e:
            logger.error(f"Error calculating layout: {e}")
            return self._get_empty_layout()

    def _get_empty_layout(self):
        return LayoutResult(
            cards_x=0,
            cards_y=0,
            cards_total=0,
            positions=[],
            rotated=False,
            efficiency=0
        )

    def calculate_sheets_needed(self, total_cards):
        """Рассчитать количество листов"""
        try:
            layout = self.calculate_layout()
            if layout.cards_total == 0:
                return 0
            sheets = (total_cards + layout.cards_total - 1) // layout.cards_total
            logger.info(f"Sheets needed: {sheets} for {total_cards} cards")
            return sheets
        except Exception as e:
            logger.error(f"Error calculating sheets needed: {e}")
            return 0