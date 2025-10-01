from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image
import os
import tempfile
from layout_calculator import LayoutCalculator

class PDFGenerator:
    def __init__(self, config):
        self.config = config
        self.sheet_width, self.sheet_height = config.get_sheet_dimensions()
        self.card_width, self.card_height = config.get_card_dimensions()
        self.gutter = config.gutter
        self.mark_length = config.mark_length
        self.matching_scheme = config.matching_scheme
        self.fit_proportions = config.fit_proportions
        self.dpi = 300

    def generate_pdf(self, front_images, back_images, output_path):
        """Сгенерировать многостраничный PDF файл"""
        if not front_images:
            raise ValueError("Нет изображений для генерации PDF")

        calculator = LayoutCalculator(
            self.sheet_width, self.sheet_height,
            self.card_width, self.card_height,
            self.config.margin, self.config.bleed, self.config.gutter,
            self.config.rotate_cards
        )

        layout = calculator.calculate_layout()
        if layout['cards_total'] == 0:
            raise ValueError("Визитки не помещаются на лист")

        # Adjust back_images based on scheme
        if back_images and self.matching_scheme != '1:1':
            if self.matching_scheme == '1:N':
                back_images = [back_images[0]] * len(front_images)
            elif self.matching_scheme == 'M:N':
                back_images = [back_images[i % len(back_images)] for i in range(len(front_images))]

        c = canvas.Canvas(output_path, pagesize=(self.sheet_width * mm, self.sheet_height * mm))

        cards_per_sheet = layout['cards_total']
        total_sheets = (len(front_images) + cards_per_sheet - 1) // cards_per_sheet

        for sheet_num in range(total_sheets):
            if sheet_num > 0:
                c.showPage()

            start_idx = sheet_num * cards_per_sheet
            end_idx = min((sheet_num + 1) * cards_per_sheet, len(front_images))
            current_front_images = front_images[start_idx:end_idx]

            self._generate_side(c, current_front_images, layout)

        if back_images:
            for sheet_num in range((len(back_images) + cards_per_sheet - 1) // cards_per_sheet):
                c.showPage()

                start_idx = sheet_num * cards_per_sheet
                end_idx = min((sheet_num + 1) * cards_per_sheet, len(back_images))
                current_back_images = back_images[start_idx:end_idx]

                self._generate_side(c, current_back_images, layout)

        c.save()

        return {
            'total_sheets': total_sheets * (2 if back_images else 1),
            'cards_per_sheet': cards_per_sheet,
            'total_cards': len(front_images)
        }

    def _generate_side(self, c, images, layout):
        """Сгенерировать одну сторону листа"""
        if self.config.add_crop_marks:
            self._add_crop_marks(c, layout)

        temp_files = []
        try:
            for i, pos in enumerate(layout['positions']):
                if i >= len(images):
                    break

                img_path = images[i]
                if not os.path.exists(img_path):
                    continue

                try:
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Resize with fit_proportions
                    target_w_mm = self.card_width + 2 * self.config.bleed
                    target_h_mm = self.card_height + 2 * self.config.bleed
                    target_w_px = int(target_w_mm * self.dpi / 25.4)
                    target_h_px = int(target_h_mm * self.dpi / 25.4)

                    if self.fit_proportions:
                        scale_x = target_w_px / img.width
                        scale_y = target_h_px / img.height
                        scale = min(scale_x, scale_y)
                        new_w = int(img.width * scale)
                        new_h = int(img.height * scale)
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    else:
                        img = img.resize((target_w_px, target_h_px), Image.Resampling.LANCZOS)

                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_path = temp_file.name
                        img.save(temp_path, 'PNG', dpi=(self.dpi, self.dpi))
                        temp_files.append(temp_path)

                    x = pos['x'] * mm
                    y = (self.sheet_height - pos['y'] - pos['height']) * mm
                    width = pos['width'] * mm
                    height = pos['height'] * mm

                    c.drawImage(temp_path, x, y, width, height)

                except Exception as e:
                    print(f"Ошибка обработки изображения {img_path}: {e}")
                    continue

            # UPDATED: Removed text labels (side_name and "Сгенерировано...")

        finally:
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

    def _add_crop_marks(self, c, layout):
        """Добавить обрезные метки для каждой визитки"""
        mark_length = self.mark_length * mm

        for pos in layout['positions']:
            bleed_mm = self.config.bleed * mm
            x = pos['x'] * mm + bleed_mm
            y = (self.sheet_height - pos['y']) * mm - bleed_mm
            width = (pos['width'] - 2 * self.config.bleed) * mm
            height = (pos['height'] - 2 * self.config.bleed) * mm

            c.line(x, y, x, y + mark_length)
            c.line(x, y, x - mark_length, y)

            c.line(x + width, y, x + width, y + mark_length)
            c.line(x + width, y, x + width + mark_length, y)

            bottom_y = y - height
            c.line(x, bottom_y, x, bottom_y - mark_length)
            c.line(x, bottom_y, x - mark_length, bottom_y)

            c.line(x + width, bottom_y, x + width, bottom_y - mark_length)
            c.line(x + width, bottom_y, x + width + mark_length, bottom_y)