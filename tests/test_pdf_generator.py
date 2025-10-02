# -*- coding: utf-8 -*-
# tests/test_pdf_generator.py
import unittest
import sys
import os
import tempfile
from unittest.mock import Mock, patch
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pdf_generator import PDFGenerator
from config import PrintConfig


class TestPDFGenerator(unittest.TestCase):

    def setUp(self):
        self.config = PrintConfig()
        self.config.sheet_size = 'A4'
        self.config.card_size = 'Стандартная (90×50)'
        self.config.margin = 5
        self.config.bleed = 3
        self.config.gutter = 0
        self.config.rotate_cards = False
        self.config.add_crop_marks = True
        self.config.mark_length = 5
        self.config.matching_scheme = '1:1'
        self.config.fit_proportions = True

        # Создаем временные изображения для тестов
        self.temp_images = []
        for i in range(3):
            img = Image.new('RGB', (90, 50), color=(i * 50, 100, 200))
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name)
            self.temp_images.append(temp_file.name)

    def tearDown(self):
        for temp_file in self.temp_images:
            try:
                os.unlink(temp_file)
            except:
                pass

    def test_init(self):
        """Тест инициализации PDFGenerator"""
        generator = PDFGenerator(self.config)
        self.assertEqual(generator.sheet_width, 210)
        self.assertEqual(generator.sheet_height, 297)
        self.assertEqual(generator.card_width, 90)
        self.assertEqual(generator.card_height, 50)
        self.assertEqual(generator.gutter, 0)
        self.assertEqual(generator.mark_length, 5)

    def test_init_custom_sizes(self):
        """Тест инициализации с пользовательскими размерами"""
        self.config.custom_sheet = True
        self.config.custom_sheet_width = 300
        self.config.custom_sheet_height = 400
        self.config.card_size = 'Произвольный'
        self.config.custom_card_width = 100
        self.config.custom_card_height = 60

        generator = PDFGenerator(self.config)
        self.assertEqual(generator.sheet_width, 300)
        self.assertEqual(generator.sheet_height, 400)
        self.assertEqual(generator.card_width, 100)
        self.assertEqual(generator.card_height, 60)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_no_images(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF без изображений"""
        generator = PDFGenerator(self.config)
        with self.assertRaises(ValueError):
            generator.generate_pdf([], [], 'output.pdf')

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_single_page(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF с одной страницей"""
        # Настраиваем mock для LayoutCalculator
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        result = generator.generate_pdf(self.temp_images, [], 'output.pdf')

        self.assertEqual(result['total_cards'], 3)
        self.assertEqual(result['total_sheets'], 1)
        self.assertEqual(result['cards_per_sheet'], 8)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_with_back_images(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF с обратными сторонами"""
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        result = generator.generate_pdf(self.temp_images, self.temp_images, 'output.pdf')

        # Листов должно быть 2: передние и задние стороны
        self.assertEqual(result['total_sheets'], 2)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_1N_scheme(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF со схемой 1:N"""
        self.config.matching_scheme = '1:N'
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        # Передаем только одно изображение для оборота
        back_images = [self.temp_images[0]]
        result = generator.generate_pdf(self.temp_images, back_images, 'output.pdf')

        # Проверяем, что генерация завершается без ошибок
        self.assertEqual(result['total_cards'], 3)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_MN_scheme(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF со схемой M:N"""
        self.config.matching_scheme = 'M:N'
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        # Передаем два изображения для оборота
        back_images = self.temp_images[:2]
        result = generator.generate_pdf(self.temp_images, back_images, 'output.pdf')

        # Проверяем, что генерация завершается без ошибок
        self.assertEqual(result['total_cards'], 3)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_no_layout(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF когда визитки не помещаются"""
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 0,
            'positions': []
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        with self.assertRaises(ValueError):
            generator.generate_pdf(self.temp_images, [], 'output.pdf')

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_with_rotation(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF с поворотом визиток"""
        self.config.rotate_cards = True
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 10,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 50, 'height': 90} for i in range(10)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        result = generator.generate_pdf(self.temp_images, [], 'output.pdf')

        self.assertEqual(result['total_cards'], 3)
        self.assertEqual(result['cards_per_sheet'], 10)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    @patch('pdf_generator.Image.open')
    def test_generate_pdf_image_processing_error(self, mock_image_open, mock_canvas, mock_layout_calculator):
        """Тест обработки ошибок при обработке изображений"""
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        # Симулируем ошибку при открытии изображения
        mock_image_open.side_effect = Exception("Image error")

        generator = PDFGenerator(self.config)

        # Должно завершиться без ошибок, но с пропуском проблемных изображений
        result = generator.generate_pdf(self.temp_images, [], 'output.pdf')
        self.assertEqual(result['total_cards'], 3)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_crop_marks(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF с обрезными метками"""
        self.config.add_crop_marks = True
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        result = generator.generate_pdf(self.temp_images, [], 'output.pdf')

        # Проверяем, что canvas.line был вызван (для отрисовки меток)
        self.assertTrue(mock_canvas.return_value.line.called)

    @patch('pdf_generator.LayoutCalculator')
    @patch('pdf_generator.canvas.Canvas')
    def test_generate_pdf_no_crop_marks(self, mock_canvas, mock_layout_calculator):
        """Тест генерации PDF без обрезных меток"""
        self.config.add_crop_marks = False
        mock_layout = Mock()
        mock_layout.calculate_layout.return_value = {
            'cards_total': 8,
            'positions': [{'x': i * 10, 'y': i * 10, 'width': 90, 'height': 50} for i in range(8)]
        }
        mock_layout_calculator.return_value = mock_layout

        generator = PDFGenerator(self.config)
        result = generator.generate_pdf(self.temp_images, [], 'output.pdf')

        # Проверяем, что canvas.line не был вызван (нет меток)
        self.assertFalse(mock_canvas.return_value.line.called)


if __name__ == '__main__':
    unittest.main()