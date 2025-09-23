from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image
import os


class PDFGenerator:
    def __init__(self, config):
        self.config = config
        self.sheet_width, self.sheet_height = config.get_sheet_dimensions()
        self.card_width, self.card_height = config.get_card_dimensions()

    def generate_pdf(self, front_images, back_images, output_path):
        """Сгенерировать PDF файл"""
        if not front_images:
            raise ValueError("Нет изображений для генерации PDF")

        # Создаем PDF документ
        c = canvas.Canvas(output_path, pagesize=(self.sheet_width * mm, self.sheet_height * mm))

        # Рассчитываем раскладку
        calculator = LayoutCalculator(
            self.sheet_width, self.sheet_height,
            self.card_width, self.card_height,
            self.config.margin, self.config.bleed,
            self.config.rotate_cards
        )

        layout = calculator.calculate_layout()
        if layout['cards_total'] == 0:
            raise ValueError("Не удалось рассчитать раскладку - визитки не помещаются на лист")

        # Генерируем лицевые стороны
        self._generate_side(c, front_images, layout, "Лицевая сторона")

        # Если есть оборотные стороны - создаем новую страницу
        if back_images:
            c.showPage()
            self._generate_side(c, back_images, layout, "Оборотная сторона")

        c.save()

        return {
            'layout': layout,
            'total_sheets': 1 + (1 if back_images else 0),
            'cards_per_sheet': layout['cards_total']
        }

    def _generate_side(self, c, images, layout, side_name):
        """Сгенерировать одну сторону листа"""
        # Добавляем обрезные метки если нужно
        if self.config.add_crop_marks:
            self._add_crop_marks(c, layout)

        # Размещаем изображения
        temp_files = []
        try:
            for i, pos in enumerate(layout['positions']):
                if i >= len(images):
                    break

                img_path = images[i]
                if not os.path.exists(img_path):
                    continue

                # Конвертируем и размещаем изображение
                img = Image.open(img_path)
                img_rgb = img.convert('RGB')

                # Сохраняем временный файл (ReportLab лучше работает с файлами)
                temp_path = f"_temp_{side_name}_{i}.png"
                img_rgb.save(temp_path, 'PNG')
                temp_files.append(temp_path)

                # Размещаем на странице
                x = pos['x'] * mm
                y = (self.sheet_height - pos['y'] - pos['height']) * mm  # Координаты ReportLab

                c.drawImage(
                    ImageReader(temp_path),
                    x, y,
                    pos['width'] * mm,
                    pos['height'] * mm
                )

            # Добавляем служебную информацию
            c.setFont("Helvetica", 8)
            c.drawString(10 * mm, 10 * mm, f"{side_name} - Сгенерировано визиточным импозером")

        finally:
            # Удаляем временные файлы
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

    def _add_crop_marks(self, c, layout):
        """Добавить обрезные метки"""
        mark_length = 5 * mm

        for pos in layout['positions']:
            x = pos['x'] * mm
            y = (self.sheet_height - pos['y']) * mm
            width = pos['width'] * mm
            height = pos['height'] * mm

            # Угловые метки
            # Левый верхний
            c.line(x, y, x, y - mark_length)
            c.line(x, y, x + mark_length, y)

            # Правый верхний
            c.line(x + width, y, x + width, y - mark_length)
            c.line(x + width, y, x + width - mark_length, y)

            # Левый нижний
            bottom_y = y - height
            c.line(x, bottom_y, x, bottom_y + mark_length)
            c.line(x, bottom_y, x + mark_length, bottom_y)

            # Правый нижний
            c.line(x + width, bottom_y, x + width, bottom_y + mark_length)
            c.line(x + width, bottom_y, x + width - mark_length, bottom_y)