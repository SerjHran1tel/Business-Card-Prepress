# tests/test_layout_calculator.py
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from layout_calculator import LayoutCalculator


class TestLayoutCalculator(unittest.TestCase):

    def test_calculate_layout_basic(self):
        """Тест базовой раскладки"""
        calculator = LayoutCalculator(
            sheet_width=210, sheet_height=297,  # A4
            card_width=90, card_height=50,  # стандартная визитка
            margin=5, bleed=3, gutter=2,
            rotate=False
        )

        result = calculator.calculate_layout()

        # Проверяем что результат имеет правильную структуру
        self.assertTrue(hasattr(result, 'cards_total'))
        self.assertTrue(hasattr(result, 'cards_x'))
        self.assertTrue(hasattr(result, 'cards_y'))
        self.assertTrue(hasattr(result, 'positions'))
        self.assertTrue(hasattr(result, 'rotated'))
        self.assertTrue(hasattr(result, 'efficiency'))

        self.assertGreater(result.cards_total, 0)
        self.assertGreater(result.efficiency, 0)
        self.assertEqual(len(result.positions), result.cards_total)

    def test_calculate_layout_rotated(self):
        """Тест раскладки с поворотом"""
        calculator = LayoutCalculator(
            sheet_width=210, sheet_height=297,
            card_width=90, card_height=50,
            margin=5, bleed=3, gutter=2,
            rotate=True
        )

        result = calculator.calculate_layout()
        self.assertTrue(hasattr(result, 'cards_total'))
        self.assertTrue(hasattr(result, 'rotated'))

    def test_calculate_layout_no_fit(self):
        """Тест когда визитки не помещаются"""
        calculator = LayoutCalculator(
            sheet_width=100, sheet_height=100,  # маленький лист
            card_width=90, card_height=50,  # большая визитка
            margin=10, bleed=3, gutter=2,
            rotate=False
        )

        result = calculator.calculate_layout()

        # Проверяем структуру результата независимо от типа
        if hasattr(result, 'cards_total'):
            # Это объект LayoutResult
            self.assertEqual(result.cards_total, 0)
            self.assertEqual(len(result.positions), 0)
        else:
            # Это словарь из _get_empty_layout()
            self.assertEqual(result['cards_total'], 0)
            self.assertEqual(len(result['positions']), 0)

    def test_calculate_sheets_needed(self):
        """Тест расчета количества листов"""
        calculator = LayoutCalculator(
            sheet_width=210, sheet_height=297,
            card_width=90, card_height=50,
            margin=5, bleed=3, gutter=2,
            rotate=False
        )

        sheets = calculator.calculate_sheets_needed(100)
        self.assertGreater(sheets, 0)

    def test_calculate_sheets_zero_cards(self):
        """Тест расчета листов для 0 визиток"""
        calculator = LayoutCalculator(
            sheet_width=210, sheet_height=297,
            card_width=90, card_height=50,
            margin=5, bleed=3, gutter=2,
            rotate=False
        )

        sheets = calculator.calculate_sheets_needed(0)
        self.assertEqual(sheets, 0)

    def test_calculate_layout_edge_case(self):
        """Тест граничного случая с минимальными размерами"""
        calculator = LayoutCalculator(
            sheet_width=100, sheet_height=60,  # минимальный лист
            card_width=45, card_height=25,  # минимальная визитка
            margin=2, bleed=1, gutter=1,
            rotate=False
        )

        result = calculator.calculate_layout()

        # Проверяем структуру результата
        if hasattr(result, 'cards_total'):
            cards_total = result.cards_total
        else:
            cards_total = result['cards_total']

        self.assertGreaterEqual(cards_total, 1)

    def test_calculate_layout_realistic(self):
        """Тест реалистичного сценария"""
        calculator = LayoutCalculator(
            sheet_width=210, sheet_height=297,  # A4
            card_width=85, card_height=55,  # евро визитка
            margin=10, bleed=3, gutter=1,
            rotate=True
        )

        result = calculator.calculate_layout()

        # Проверяем что результат валиден
        if hasattr(result, 'cards_total'):
            self.assertGreater(result.cards_total, 0)
            self.assertIsInstance(result.positions, list)
        else:
            self.assertGreater(result['cards_total'], 0)
            self.assertIsInstance(result['positions'], list)


if __name__ == '__main__':
    unittest.main()