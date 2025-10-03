# tests/test_pdf_generator.py
import unittest
import sys
import os
import tempfile
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pdf_generator import PDFGenerator
from config import PrintConfig


class TestPDFGenerator(unittest.TestCase):

    def setUp(self):
        self.config = PrintConfig()
        self.temp_dir = tempfile.mkdtemp()
        self.test_images = []

    def create_test_image(self, size=(100, 100)):
        """Создать тестовое изображение"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img = Image.new('RGB', size, color='red')
        img.save(temp_file.name)
        self.test_images.append(temp_file.name)
        return temp_file.name

    def tearDown(self):
        """Очистка временных файлов"""
        for img_path in self.test_images:
            try:
                os.unlink(img_path)
            except:
                pass

    def test_pdf_generator_init(self):
        """Тест инициализации PDF генератора"""
        generator = PDFGenerator(self.config)
        self.assertEqual(generator.sheet_width, 210)
        self.assertEqual(generator.sheet_height, 297)

    def test_generate_pdf_basic(self):
        """Тест генерации PDF с базовыми параметрами"""
        generator = PDFGenerator(self.config)
        front_images = [self.create_test_image() for _ in range(3)]
        back_images = [self.create_test_image() for _ in range(3)]

        output_path = os.path.join(self.temp_dir, "test_output.pdf")

        result = generator.generate_pdf(front_images, back_images, output_path)

        self.assertIsInstance(result, dict)
        self.assertIn('total_sheets', result)
        self.assertIn('total_cards', result)
        self.assertTrue(os.path.exists(output_path))

    def test_generate_pdf_no_back(self):
        """Тест генерации PDF без оборотных сторон"""
        generator = PDFGenerator(self.config)
        front_images = [self.create_test_image() for _ in range(2)]

        output_path = os.path.join(self.temp_dir, "test_output_no_back.pdf")

        result = generator.generate_pdf(front_images, [], output_path)

        self.assertIsInstance(result, dict)
        self.assertTrue(os.path.exists(output_path))

    def test_generate_pdf_scheme_1n(self):
        """Тест генерации PDF со схемой 1:N"""
        self.config.matching_scheme = '1:N'
        generator = PDFGenerator(self.config)

        front_images = [self.create_test_image() for _ in range(3)]
        back_images = [self.create_test_image()]  # одна рубашка

        output_path = os.path.join(self.temp_dir, "test_output_1n.pdf")

        result = generator.generate_pdf(front_images, back_images, output_path)
        self.assertTrue(os.path.exists(output_path))

    def test_generate_pdf_no_images(self):
        """Тест генерации PDF без изображений"""
        generator = PDFGenerator(self.config)
        output_path = os.path.join(self.temp_dir, "test_empty.pdf")

        with self.assertRaises(ValueError):
            generator.generate_pdf([], [], output_path)


if __name__ == '__main__':
    unittest.main()