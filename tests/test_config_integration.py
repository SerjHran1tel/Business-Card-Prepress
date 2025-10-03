# tests/test_config_integration.py
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import PrintConfig
from layout_calculator import LayoutCalculator
from pdf_generator import PDFGenerator


class TestConfigIntegration(unittest.TestCase):

    def test_config_with_layout_calculator(self):
        """Тест интеграции конфига с калькулятором раскладки"""
        config = PrintConfig()
        config.sheet_size = 'A4'
        config.card_size = 'Стандартная (90×50)'
        config.margin = 5
        config.bleed = 3
        config.gutter = 2

        sheet_w, sheet_h = config.get_sheet_dimensions()
        card_w, card_h = config.get_card_dimensions()

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            config.margin, config.bleed, config.gutter,
            config.rotate_cards
        )

        result = calculator.calculate_layout()
        # Проверяем что результат содержит ожидаемые атрибуты
        self.assertTrue(hasattr(result, 'cards_total'))
        self.assertTrue(hasattr(result, 'cards_x'))
        self.assertTrue(hasattr(result, 'cards_y'))
        self.assertTrue(hasattr(result, 'positions'))
        self.assertTrue(hasattr(result, 'rotated'))
        self.assertTrue(hasattr(result, 'efficiency'))
        self.assertGreater(result.cards_total, 0)

    def test_config_with_pdf_generator(self):
        """Тест интеграции конфига с PDF генератором"""
        config = PrintConfig()
        generator = PDFGenerator(config)

        self.assertEqual(generator.sheet_width, 210)
        self.assertEqual(generator.sheet_height, 297)
        self.assertEqual(generator.card_width, 90)
        self.assertEqual(generator.card_height, 50)

    def test_custom_sizes_integration(self):
        """Тест интеграции с произвольными размерами"""
        config = PrintConfig()
        config.custom_sheet = True
        config.custom_sheet_width = 300
        config.custom_sheet_height = 400
        config.card_size = 'Произвольный'
        config.custom_card_width = 80
        config.custom_card_height = 40

        sheet_w, sheet_h = config.get_sheet_dimensions()
        card_w, card_h = config.get_card_dimensions()

        self.assertEqual(sheet_w, 300)
        self.assertEqual(sheet_h, 400)
        self.assertEqual(card_w, 80)
        self.assertEqual(card_h, 40)

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            config.margin, config.bleed, config.gutter,
            config.rotate_cards
        )

        result = calculator.calculate_layout()
        # Проверяем структуру результата
        self.assertTrue(hasattr(result, 'cards_total'))
        self.assertTrue(hasattr(result, 'positions'))
        self.assertIsInstance(result.cards_total, int)
        self.assertIsInstance(result.positions, list)

    def test_different_sheet_sizes(self):
        """Тест различных размеров листов"""
        test_sizes = [
            ('A4', (210, 297)),
            ('A3', (297, 420)),
            ('Letter', (216, 279))
        ]

        for sheet_name, expected_size in test_sizes:
            with self.subTest(sheet_name=sheet_name):
                config = PrintConfig()
                config.sheet_size = sheet_name

                actual_size = config.get_sheet_dimensions()
                self.assertEqual(actual_size, expected_size)

    def test_different_card_sizes(self):
        """Тест различных размеров визиток"""
        test_sizes = [
            ('Стандартная (90×50)', (90, 50)),
            ('Евро (85×55)', (85, 55)),
            ('Квадратная (90×90)', (90, 90))
        ]

        for card_name, expected_size in test_sizes:
            with self.subTest(card_name=card_name):
                config = PrintConfig()
                config.card_size = card_name

                actual_size = config.get_card_dimensions()
                self.assertEqual(actual_size, expected_size)


if __name__ == '__main__':
    unittest.main()