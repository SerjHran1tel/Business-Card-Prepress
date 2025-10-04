"""
Генератор PDF с раскладкой визиток
"""
import tempfile
import logging
from pathlib import Path
from typing import List, Optional
from copy import deepcopy

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from PyPDF2 import PdfReader, PdfWriter

from .models import PrintSettings, CardQuantity, Orientation, PageFormat
from .layout_calculator import LayoutCalculator

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self, settings: PrintSettings):
        self.settings = self._apply_orientation(settings)
        self.cols, self.rows, self.x_offset, self.y_offset = \
            LayoutCalculator.calculate_layout(self.settings)
        self.temp_files = []

    def _apply_orientation(self, settings: PrintSettings) -> PrintSettings:
        portrait_page = PageFormat(
            settings.page_format.name,
            settings.page_format.width,
            settings.page_format.height
        )
        landscape_page = PageFormat(
            settings.page_format.name,
            settings.page_format.height,
            settings.page_format.width
        )

        if settings.orientation == Orientation.LANDSCAPE:
            new_settings = deepcopy(settings)
            new_settings.page_format = landscape_page
            logger.info("Принудительный выбор: Landscape")
            return new_settings
        elif settings.orientation == Orientation.PORTRAIT:
            new_settings = deepcopy(settings)
            new_settings.page_format = portrait_page
            logger.info("Принудительный выбор: Portrait")
            return new_settings
        else:  # AUTO
            # Portrait
            portrait_settings = deepcopy(settings)
            portrait_settings.page_format = portrait_page
            p_cols, p_rows, _, _ = LayoutCalculator.calculate_layout(portrait_settings)
            p_cards = p_cols * p_rows

            # Landscape
            landscape_settings = deepcopy(settings)
            landscape_settings.page_format = landscape_page
            l_cols, l_rows, _, _ = LayoutCalculator.calculate_layout(landscape_settings)
            l_cards = l_cols * l_rows

            if l_cards > p_cards:
                logger.info("Автоматический выбор: Landscape (больше визиток на листе)")
                return landscape_settings
            else:
                logger.info("Автоматический выбор: Portrait")
                return portrait_settings

    def __del__(self):
        for temp_file in self.temp_files:
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            except:
                pass

    def create_imposition(self, front_cards: List[CardQuantity],
                         back_cards: Optional[List[CardQuantity]],
                         output_path: Path) -> bool:
        logger.info(f"Начало создания PDF: {output_path}")
        try:
            front_files = []
            for card in front_cards:
                front_files.extend([card.file_path] * card.quantity)

            back_files = None
            if back_cards:
                back_files = []
                for card in back_cards:
                    back_files.extend([card.file_path] * card.quantity)

            cards_per_sheet = self.cols * self.rows
            total_sheets = (len(front_files) + cards_per_sheet - 1) // cards_per_sheet

            logger.info(f"Всего визиток: {len(front_files)}, листов: {total_sheets}")

            with tempfile.NamedTemporaryFile(suffix='_front.pdf', delete=False) as f:
                temp_front = Path(f.name)
                self.temp_files.append(temp_front)

            with tempfile.NamedTemporaryFile(suffix='_back.pdf', delete=False) as f:
                temp_back = Path(f.name)
                self.temp_files.append(temp_back)

            self._generate_side(front_files, temp_front, "Лицевая сторона")

            if back_files and self.settings.matching_mode.value != 'one_to_many':
                self._generate_side(back_files, temp_back, "Оборотная сторона", flip=True)
            elif back_files and self.settings.matching_mode.value == 'one_to_many':
                self._generate_single_back(back_files[0], len(front_files), temp_back)

            self._merge_front_back(temp_front, temp_back if back_files else None, output_path)

            logger.info(f"PDF успешно создан: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при создании PDF: {e}")
            return False

    def _generate_side(self, files: List[Path], output: Path, title: str, flip: bool = False):
        page_width = self.settings.page_format.width * mm
        page_height = self.settings.page_format.height * mm

        c = canvas.Canvas(str(output), pagesize=(page_width, page_height))
        c.setTitle(title)

        cards_per_sheet = self.cols * self.rows

        for sheet_idx in range((len(files) + cards_per_sheet - 1) // cards_per_sheet):
            start_idx = sheet_idx * cards_per_sheet
            end_idx = min(start_idx + cards_per_sheet, len(files))
            sheet_files = files[start_idx:end_idx]

            for idx, file in enumerate(sheet_files):
                row = idx // self.cols
                col = idx % self.cols

                if flip:
                    col = self.cols - 1 - col

                x = (self.x_offset + col * (self.settings.card_size.width + self.settings.gap)) * mm
                y = (self.y_offset + row * (self.settings.card_size.height + self.settings.gap)) * mm

                self._draw_card(c, file, x, y)

                if self.settings.crop_marks:
                    self._draw_crop_marks(c, x, y)

            c.showPage()

        c.save()

    def _generate_single_back(self, back_file: Path, count: int, output: Path):
        page_width = self.settings.page_format.width * mm
        page_height = self.settings.page_format.height * mm

        c = canvas.Canvas(str(output), pagesize=(page_width, page_height))
        c.setTitle("Оборотная сторона")

        cards_per_sheet = self.cols * self.rows
        total_sheets = (count + cards_per_sheet - 1) // cards_per_sheet

        for sheet_idx in range(total_sheets):
            start_idx = sheet_idx * cards_per_sheet
            remaining = min(cards_per_sheet, count - start_idx)

            for idx in range(remaining):
                row = idx // self.cols
                col = self.cols - 1 - (idx % self.cols)

                x = (self.x_offset + col * (self.settings.card_size.width + self.settings.gap)) * mm
                y = (self.y_offset + row * (self.settings.card_size.height + self.settings.gap)) * mm

                self._draw_card(c, back_file, x, y)

                if self.settings.crop_marks:
                    self._draw_crop_marks(c, x, y)

            c.showPage()

        c.save()

    def _draw_card(self, c: canvas.Canvas, image_path: Path, x: float, y: float):
        card_width = self.settings.card_size.width * mm
        card_height = self.settings.card_size.height * mm

        try:
            from processing.image_processor import ImageProcessor
            target_size = (self.settings.card_size.width, self.settings.card_size.height)
            img_reader = ImageProcessor.process_image_for_print(image_path, self.settings, target_size)

            c.drawImage(img_reader, x, y, width=card_width, height=card_height,
                       preserveAspectRatio=True, mask='auto')

        except Exception as e:
            logger.error(f"Ошибка отрисовки визитки {image_path}: {e}")
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(x, y, card_width, card_height, fill=1)
            c.setFillColorRGB(1, 0, 0)
            c.setFont("Helvetica", 6)
            c.drawString(x + 2, y + card_height / 2, f"Error: {image_path.name}")

    def _draw_crop_marks(self, c: canvas.Canvas, x: float, y: float):
        card_width = self.settings.card_size.width * mm
        card_height = self.settings.card_size.height * mm
        mark_len = self.settings.crop_mark_length * mm
        offset = self.settings.crop_mark_offset * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.25)

        corners = [
            (x - offset - mark_len, y, x - offset, y),
            (x, y - offset - mark_len, x, y - offset),
            (x + card_width + offset, y, x + card_width + offset + mark_len, y),
            (x + card_width, y - offset - mark_len, x + card_width, y - offset),
            (x - offset - mark_len, y + card_height, x - offset, y + card_height),
            (x, y + card_height + offset, x, y + card_height + offset + mark_len),
            (x + card_width + offset, y + card_height, x + card_width + offset + mark_len, y + card_height),
            (x + card_width, y + card_height + offset, x + card_width, y + card_height + offset + mark_len)
        ]

        for start_x, start_y, end_x, end_y in corners:
            c.line(start_x, start_y, end_x, end_y)

    def _merge_front_back(self, front_pdf: Path, back_pdf: Optional[Path], output: Path):
        try:
            writer = PdfWriter()
            front_reader = PdfReader(str(front_pdf))

            if back_pdf and back_pdf.exists():
                back_reader = PdfReader(str(back_pdf))
                max_pages = max(len(front_reader.pages), len(back_reader.pages))

                for i in range(max_pages):
                    if i < len(front_reader.pages):
                        writer.add_page(front_reader.pages[i])
                    if i < len(back_reader.pages):
                        writer.add_page(back_reader.pages[i])
            else:
                for page in front_reader.pages:
                    writer.add_page(page)

            with open(output, 'wb') as f:
                writer.write(f)

        except Exception as e:
            logger.error(f"Ошибка объединения PDF: {e}")
            raise