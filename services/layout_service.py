# -*- coding: utf-8 -*-
# services/layout_service.py
from layout_calculator import LayoutCalculator
from core.models import LayoutRequest, LayoutResponse


class LayoutService:
    async def calculate_layout(self, request: LayoutRequest) -> LayoutResponse:
        """Расчет раскладки визиток на листе"""
        try:
            calculator = LayoutCalculator(
                request.sheet_width, request.sheet_height,
                request.card_width, request.card_height,
                request.margin, request.bleed, request.gutter,
                request.rotate
            )

            layout = calculator.calculate_layout()

            return LayoutResponse(
                success=True,
                layout={
                    "cards_x": layout.cards_x,
                    "cards_y": layout.cards_y,
                    "cards_total": layout.cards_total,
                    "rotated": layout.rotated,
                    "efficiency": layout.efficiency,
                    "positions": layout.positions
                }
            )

        except Exception as e:
            return LayoutResponse(
                success=False,
                layout={},
                error=str(e)
            )