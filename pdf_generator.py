from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image
import os
import tempfile
from layout_calculator import LayoutCalculator  # Добавляем импорт


class PDFGenerator:
    def __init__(self, config):
        self.config = config
        self.sheet_width, self.sheet_height = config.get_sheet_dimensions()
        self.card_width, self.card_height = config.get_card_dimensions()

    def generate_pdf(self, front_images, back_images, output_path):
        """Сгенерировать многостраничный PDF файл"""
        if not front_images:
            raise ValueError("Нет изображений для генерации PDF")

        # Рассчитываем раскладку
        calculator = LayoutCalculator(
            self.sheet_width, self.sheet_height,
            self.card_width, self.card_height,
            self.config.margin, self.config.bleed,
            self.config.rotate_cards
        )

        layout = calculator.calculate_layout()
        if layout['cards_total'] == 0:
            raise ValueError("Визитки не помещаются на лист")

        # Создаем PDF документ
        c = canvas.Canvas(output_path, pagesize=(self.sheet_width * mm, self.sheet_height * mm))

        # Рассчитываем количество листов
        cards_per_sheet = layout['cards_total']
        total_sheets = (len(front_images) + cards_per_sheet - 1) // cards_per_sheet

        # Генерируем листы с лицевыми сторонами
        for sheet_num in range(total_sheets):
            if sheet_num > 0:
                c.showPage()

            start_idx = sheet_num * cards_per_sheet
            end_idx = min((sheet_num + 1) * cards_per_sheet, len(front_images))
            current_front_images = front_images[start_idx:end_idx]

            self._generate_side(c, current_front_images, layout, f"Лист {sheet_num + 1} - Лицевые стороны")

        # Генерируем листы с оборотными сторонами (если есть)
        if back_images:
            for sheet_num in range(total_sheets):
                c.showPage()

                start_idx = sheet_num * cards_per_sheet
                end_idx = min((sheet_num + 1) * cards_per_sheet, len(back_images))
                current_back_images = back_images[start_idx:end_idx]

                self._generate_side(c, current_back_images, layout, f"Лист {sheet_num + 1} - Оборотные стороны")

        c.save()

        return {
            'total_sheets': total_sheets * (2 if back_images else 1),
            'cards_per_sheet': cards_per_sheet,
            'total_cards': len(front_images)
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

                try:
                    # Открываем и конвертируем изображение
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Создаем временный файл
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_path = temp_file.name
                        img.save(temp_path, 'PNG', dpi=(300, 300))
                        temp_files.append(temp_path)

                    # Размещаем на странице
                    x = pos['x'] * mm
                    y = (self.sheet_height - pos['y'] - pos['height']) * mm
                    width = pos['width'] * mm
                    height = pos['height'] * mm

                    c.drawImage(temp_path, x, y, width, height)

                except Exception as e:
                    print(f"Ошибка обработки изображения {img_path}: {e}")
                    continue

            # Добавляем служебную информацию
            c.setFont("Helvetica", 8)
            c.drawString(10 * mm, 10 * mm, side_name)
            c.drawString(10 * mm, 8 * mm, f"Сгенерировано визиточным импозером")

        finally:
            # Удаляем временные файлы
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def _add_crop_marks(self, c, layout):
        """Добавить обрезные метки для каждой визитки"""
        mark_length = 5  # мм

        for pos in layout['positions']:
            x = pos['x'] * mm
            y = (self.sheet_height - pos['y']) * mm
            width = pos['width'] * mm
            height = pos['height'] * mm

            # Угловые метки
            # Левый верхний
            c.line(x, y, x, y - mark_length * mm)
            c.line(x, y, x + mark_length * mm, y)

            # Правый верхний
            c.line(x + width, y, x + width, y - mark_length * mm)
            c.line(x + width, y, x + width - mark_length * mm, y)

            # Левый нижний
            bottom_y = y - height
            c.line(x, bottom_y, x, bottom_y + mark_length * mm)
            c.line(x, bottom_y, x + mark_length * mm, bottom_y)

            # Правый нижний
            c.line(x + width, bottom_y, x + width, bottom_y + mark_length * mm)
            c.line(x + width, bottom_y, x + width - mark_length * mm, bottom_y)