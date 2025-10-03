# tests/test_image_utils_validation.py
import unittest
import sys
import os
import tempfile
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from image_utils import validate_image_pairs_extended, generate_validation_report, ValidationResult


class TestImageUtilsValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def create_test_image_info(self, size=(100, 100), dpi=(300, 300)):
        """Создать тестовую информацию об изображении"""
        return {
            'filename': 'test.jpg',
            'size': size,
            'dpi': dpi,
            'mode': 'RGB',
            'color_space': 'RGB',
            'color_profile': 'None'
        }

    def test_validate_pairs_extended_1to1(self):
        """Тест расширенной валидации схемы 1:1"""
        front_infos = [self.create_test_image_info() for _ in range(3)]
        back_infos = [self.create_test_image_info() for _ in range(3)]

        result = validate_image_pairs_extended(
            front_infos, back_infos, '1:1', False,
            card_width=90, card_height=50, bleed=3
        )

        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(len(result.errors), 0)

    def test_validate_pairs_extended_mismatch(self):
        """Тест валидации с несоответствием количества"""
        front_infos = [self.create_test_image_info() for _ in range(3)]
        back_infos = [self.create_test_image_info() for _ in range(2)]  # разное количество

        result = validate_image_pairs_extended(
            front_infos, back_infos, '1:1', False,
            card_width=90, card_height=50, bleed=3
        )

        self.assertGreater(len(result.warnings), 0)

    def test_validate_pairs_extended_low_dpi(self):
        """Тест валидации с низким DPI"""
        front_info = self.create_test_image_info(dpi=(72, 72))  # низкий DPI

        result = validate_image_pairs_extended(
            [front_info], [], '1:1', False,
            card_width=90, card_height=50, bleed=3, min_dpi=300
        )

        self.assertGreater(len(result.dpi_issues), 0)

    def test_validate_pairs_extended_safe_zone(self):
        """Тест валидации безопасной зоны"""
        # Маленькое изображение для большой визитки
        front_info = self.create_test_image_info(size=(50, 25))

        result = validate_image_pairs_extended(
            [front_info], [], '1:1', False,
            card_width=90, card_height=50, bleed=3
        )

        self.assertGreater(len(result.safe_zone_issues), 0)

    def test_generate_validation_report_empty(self):
        """Тест генерации пустого отчета"""
        result = ValidationResult([], [], [], [], [], [])
        report = generate_validation_report(result)

        self.assertIn("Все проверки пройдены успешно", report)

    def test_generate_validation_report_with_errors(self):
        """Тест генерации отчета с ошибками"""
        result = ValidationResult(
            errors=['Ошибка 1', 'Ошибка 2'],
            warnings=['Предупреждение 1'],
            infos=['Информация 1'],
            dpi_issues=[],
            color_issues=[],
            safe_zone_issues=[]
        )

        report = generate_validation_report(result)

        self.assertIn("🚨 ОШИБКИ:", report)
        self.assertIn("⚠️ ПРЕДУПРЕЖДЕНИЯ:", report)
        self.assertIn("ℹ️ ИНФОРМАЦИЯ:", report)


if __name__ == '__main__':
    unittest.main()