"""
Business Card Imposition System
Автоматическая раскладка визиток на печатные листы
"""

from pathlib import Path
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import json
import re
import logging
import tempfile
from io import BytesIO

from PIL import Image, ImageCms
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger.warning("pdf2image не установлен, PDF превью недоступно")

try:
    import fitz  # PyMuPDF
    PYPDF2_SUPPORT = True
except ImportError:
    PYPDF2_SUPPORT = False
    logger.warning("PyMuPDF не установлен, используем базовую обработку PDF")


class Orientation(Enum):
    """Ориентация визитки"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


class MatchingMode(Enum):
    """Режимы сопоставления лицо-оборот"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class ColorMode(Enum):
    """Цветовые режимы"""
    RGB = "rgb"
    CMYK = "cmyk"


@dataclass
class PageFormat:
    """Формат печатного листа"""
    name: str
    width: float  # в мм
    height: float  # в мм

    @classmethod
    def get_standard_formats(cls) -> Dict[str, 'PageFormat']:
        return {
            'A4': cls('A4', 210, 297),
            'A3': cls('A3', 297, 420),
            'SRA3': cls('SRA3', 320, 450),
            'SRA4': cls('SRA4', 225, 320),
        }


@dataclass
class CardSize:
    """Размер визитки"""
    width: float  # в мм
    height: float  # в мм

    @classmethod
    def get_standard_sizes(cls) -> Dict[str, 'CardSize']:
        return {
            'Standard EU': cls(85, 55),
            'Standard RU': cls(90, 50),
            'Standard US': cls(89, 51),
            'Square': cls(70, 70),
        }


@dataclass
class CardQuantity:
    """Количество копий визитки"""
    file_path: Path
    quantity: int = 1


@dataclass
class PrintSettings:
    """Настройки печати"""
    page_format: PageFormat
    card_size: CardSize
    margin_top: float = 10.0  # мм
    margin_bottom: float = 10.0
    margin_left: float = 10.0
    margin_right: float = 10.0
    bleed: float = 3.0  # вылеты
    gap: float = 2.0  # зазор между визитками
    crop_marks: bool = True
    crop_mark_length: float = 5.0  # мм
    crop_mark_offset: float = 2.0  # мм
    orientation: Orientation = Orientation.AUTO
    matching_mode: MatchingMode = MatchingMode.ONE_TO_ONE
    strict_name_matching: bool = True
    dpi: int = 300  # Разрешение для растровых изображений
    color_mode: ColorMode = ColorMode.RGB  # Цветовой режим
    output_dpi: int = 300  # Разрешение выходного PDF


class ValidationResult:
    """Результат валидации файлов"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"Validation error: {message}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        logger.warning(f"Validation warning: {message}")

    def get_report(self) -> str:
        report = []
        if self.errors:
            report.append("ОШИБКИ:")
            for err in self.errors:
                report.append(f"  ❌ {err}")
        if self.warnings:
            report.append("\nПРЕДУПРЕЖДЕНИЯ:")
            for warn in self.warnings:
                report.append(f"  ⚠️ {warn}")
        if self.is_valid and not self.warnings:
            report.append("✅ Все файлы прошли валидацию успешно")
        return "\n".join(report)


class FileManager:
    """Управление файлами изображений"""

    SUPPORTED_FORMATS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.eps'}

    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, str]:
        """Проверка целостности файла"""
        try:
            if not file_path.exists():
                return False, "Файл не существует"

            # Проверка размера файла
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "Файл пустой"
            if file_size > 100 * 1024 * 1024:  # 100MB
                return False, "Файл слишком большой (>100MB)"

            # Проверка формата
            if file_path.suffix.lower() not in FileManager.SUPPORTED_FORMATS:
                return False, f"Неподдерживаемый формат: {file_path.suffix}"

            # Проверка содержимого
            if file_path.suffix.lower() == '.pdf':
                if PYPDF2_SUPPORT:
                    try:
                        doc = fitz.open(str(file_path))
                        if len(doc) == 0:
                            return False, "PDF файл поврежден"
                        doc.close()
                    except Exception as e:
                        return False, f"Ошибка чтения PDF: {str(e)}"
            else:
                try:
                    with Image.open(file_path) as img:
                        img.verify()  # Проверка целостности
                except Exception as e:
                    return False, f"Изображение повреждено: {str(e)}"

            return True, "OK"
        except Exception as e:
            return False, f"Ошибка валидации: {str(e)}"

    @staticmethod
    def scan_directory(directory: Path) -> List[Path]:
        """Сканирование директории на наличие поддерживаемых файлов"""
        if not directory.exists():
            return []

        files = []
        for file in sorted(directory.iterdir()):
            if file.suffix.lower() in FileManager.SUPPORTED_FORMATS:
                is_valid, message = FileManager.validate_file(file)
                if is_valid:
                    files.append(file)
                else:
                    logger.warning(f"Пропущен поврежденный файл {file.name}: {message}")
        return files

    @staticmethod
    def normalize_filename(filename: str) -> str:
        """Нормализация имени файла для сравнения"""
        name = Path(filename).stem.lower()
        name = re.sub(r'[^\w]', '', name)
        return name

    @staticmethod
    def match_files(front_files: List[Path], back_files: List[Path],
                   strict: bool = True) -> Dict[Path, Optional[Path]]:
        """
        Сопоставление лицевых и оборотных файлов
        Возвращает словарь {front_file: back_file or None}
        """
        matches = {}

        if strict:
            back_dict = {f.stem: f for f in back_files}
            for front_file in front_files:
                matches[front_file] = back_dict.get(front_file.stem)
        else:
            if len(back_files) == 0:
                for front_file in front_files:
                    matches[front_file] = None
            elif len(front_files) == len(back_files):
                for front_file, back_file in zip(front_files, back_files):
                    matches[front_file] = back_file
            else:
                back_dict = {FileManager.normalize_filename(f.name): f for f in back_files}
                for front_file in front_files:
                    normalized = FileManager.normalize_filename(front_file.name)
                    matches[front_file] = back_dict.get(normalized)
                    if matches[front_file] is None and back_files:
                        matches[front_file] = back_files[0]

        return matches

    @staticmethod
    def validate_files(front_dir: Path, back_dir: Path,
                      matching_mode: MatchingMode,
                      strict_matching: bool = True) -> ValidationResult:
        """Валидация файлов лицевой и оборотной сторон"""
        result = ValidationResult()

        if not front_dir.exists():
            result.add_error(f"Директория лицевых сторон не найдена: {front_dir}")
            return result

        front_files = FileManager.scan_directory(front_dir)
        if not front_files:
            result.add_error(f"Не найдено файлов в директории: {front_dir}")
            return result

        # Проверка каждого файла
        for file in front_files:
            is_valid, message = FileManager.validate_file(file)
            if not is_valid:
                result.add_error(f"Лицевая сторона {file.name}: {message}")

        if matching_mode == MatchingMode.ONE_TO_ONE:
            if not back_dir.exists():
                result.add_error(f"Директория оборотных сторон не найдена: {back_dir}")
                return result

            back_files = FileManager.scan_directory(back_dir)
            if not back_files:
                result.add_error(f"Не найдено файлов в директории: {back_dir}")
                return result

            # Проверка каждого файла
            for file in back_files:
                is_valid, message = FileManager.validate_file(file)
                if not is_valid:
                    result.add_error(f"Оборотная сторона {file.name}: {message}")

            matches = FileManager.match_files(front_files, back_files, strict_matching)

            missing_backs = [f.name for f, b in matches.items() if b is None]
            if missing_backs and strict_matching:
                result.add_warning(
                    f"Отсутствуют оборотные стороны для: {', '.join(missing_backs)}\n"
                    f"Попробуйте отключить строгое совпадение имен"
                )

            back_names = {f.name for f in back_files}
            front_names = {f.name for f in front_files}
            extra_backs = back_names - front_names
            if extra_backs and strict_matching:
                result.add_warning(
                    f"Оборотные стороны без пары: {', '.join(extra_backs)}"
                )

        elif matching_mode == MatchingMode.ONE_TO_MANY:
            if back_dir.exists():
                back_files = FileManager.scan_directory(back_dir)
                if len(back_files) != 1:
                    result.add_error(
                        f"В режиме ONE_TO_MANY должен быть ровно 1 файл оборота, "
                        f"найдено: {len(back_files)}"
                    )

        return result


class ImageProcessor:
    """Обработчик изображений с поддержкой CMYK и DPI"""

    @staticmethod
    def convert_to_cmyk(image: Image.Image) -> Image.Image:
        """Конвертация изображения в CMYK"""
        try:
            # Создаем CMYK профиль (условный, для печати)
            cmyk_profile = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(image, cmyk_profile, cmyk_profile, outputMode='CMYK')
        except Exception as e:
            logger.warning(f"Не удалось конвертировать в CMYK: {e}")
            return image.convert('CMYK')

    @staticmethod
    def process_image_for_print(image_path: Path, settings: PrintSettings,
                               target_size: Tuple[float, float]) -> ImageReader:
        """Обработка изображения для печати с учетом DPI и цветового режима"""
        try:
            if image_path.suffix.lower() == '.pdf':
                # Обработка PDF
                if PDF_SUPPORT:
                    images = convert_from_path(
                        str(image_path),
                        dpi=settings.dpi,
                        first_page=1,
                        last_page=1
                    )
                    if images:
                        img = images[0]
                    else:
                        raise Exception("Не удалось конвертировать PDF")
                else:
                    raise Exception("PDF поддержка не установлена")
            else:
                img = Image.open(image_path)

            # Конвертация в CMYK если нужно
            if settings.color_mode == ColorMode.CMYK:
                img = ImageProcessor.convert_to_cmyk(img)

            # Масштабирование с учетом DPI
            target_width_px = int(target_size[0] * settings.dpi / 25.4)  # мм в пиксели
            target_height_px = int(target_size[1] * settings.dpi / 25.4)

            img.thumbnail((target_width_px, target_height_px), Image.Resampling.LANCZOS)

            # Сохраняем во временный буфер
            buffer = BytesIO()
            if settings.color_mode == ColorMode.CMYK:
                img.save(buffer, format='TIFF', dpi=(settings.dpi, settings.dpi))
            else:
                img.save(buffer, format='PNG', dpi=(settings.dpi, settings.dpi))

            buffer.seek(0)
            return ImageReader(buffer)

        except Exception as e:
            logger.error(f"Ошибка обработки изображения {image_path}: {e}")
            # Создаем заглушку
            buffer = BytesIO()
            placeholder = Image.new('RGB', (100, 100), color='lightgray')
            placeholder.save(buffer, format='PNG')
            buffer.seek(0)
            return ImageReader(buffer)


class LayoutCalculator:
    """Расчет раскладки визиток на листе"""

    @staticmethod
    def calculate_layout(settings: PrintSettings) -> Tuple[int, int, float, float]:
        """
        Рассчитывает количество визиток по горизонтали и вертикали
        Возвращает: (cols, rows, x_offset, y_offset)
        """
        available_width = (settings.page_format.width -
                          settings.margin_left - settings.margin_right)
        available_height = (settings.page_format.height -
                           settings.margin_top - settings.margin_bottom)

        card_width = settings.card_size.width + settings.gap
        card_height = settings.card_size.height + settings.gap

        cols = int(available_width // card_width)
        rows = int(available_height // card_height)

        # Минимум 1 визитка на листе
        cols = max(1, cols)
        rows = max(1, rows)

        total_cards_width = cols * card_width - settings.gap
        total_cards_height = rows * card_height - settings.gap

        x_offset = settings.margin_left + (available_width - total_cards_width) / 2
        y_offset = settings.margin_bottom + (available_height - total_cards_height) / 2

        logger.info(f"Раскладка: {cols}x{rows} визиток, offset: ({x_offset:.1f}, {y_offset:.1f})")
        return cols, rows, x_offset, y_offset


class PDFGenerator:
    """Генератор PDF с раскладкой"""

    def __init__(self, settings: PrintSettings):
        self.settings = settings
        self.cols, self.rows, self.x_offset, self.y_offset = \
            LayoutCalculator.calculate_layout(settings)
        self.temp_files = []  # Для очистки временных файлов

    def __del__(self):
        """Очистка временных файлов"""
        for temp_file in self.temp_files:
            try:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            except:
                pass

    def create_imposition(self, front_cards: List[CardQuantity],
                         back_cards: Optional[List[CardQuantity]],
                         output_path: Path) -> bool:
        """Создание PDF с раскладкой"""
        logger.info(f"Начало создания PDF: {output_path}")
        try:
            # Разворачиваем список с учетом количества
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

            # Создаем временные PDF
            with tempfile.NamedTemporaryFile(suffix='_front.pdf', delete=False) as f:
                temp_front = Path(f.name)
                self.temp_files.append(temp_front)

            with tempfile.NamedTemporaryFile(suffix='_back.pdf', delete=False) as f:
                temp_back = Path(f.name)
                self.temp_files.append(temp_back)

            # Генерируем лицевую сторону
            self._generate_side(front_files, temp_front, "Лицевая сторона")

            # Генерируем оборотную сторону
            if back_files and self.settings.matching_mode != MatchingMode.ONE_TO_MANY:
                self._generate_side(back_files, temp_back, "Оборотная сторона", flip=True)
            elif back_files and self.settings.matching_mode == MatchingMode.ONE_TO_MANY:
                self._generate_single_back(back_files[0], len(front_files),
                                          temp_back, "Оборотная сторона")

            # Объединяем в финальный PDF
            self._merge_front_back(temp_front, temp_back if back_files else None,
                                  output_path)

            logger.info(f"PDF успешно создан: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при создании PDF: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_side(self, files: List[Path], output: Path,
                       title: str, flip: bool = False):
        """Генерация одной стороны"""
        logger.info(f"Генерация {title}, файлов: {len(files)}")

        page_width = self.settings.page_format.width * mm
        page_height = self.settings.page_format.height * mm

        c = canvas.Canvas(str(output), pagesize=(page_width, page_height))
        c.setTitle(title)

        cards_per_sheet = self.cols * self.rows

        for sheet_idx in range((len(files) + cards_per_sheet - 1) // cards_per_sheet):
            start_idx = sheet_idx * cards_per_sheet
            end_idx = min(start_idx + cards_per_sheet, len(files))
            sheet_files = files[start_idx:end_idx]

            logger.info(f"Лист {sheet_idx + 1}: визитки {start_idx + 1}-{end_idx}")

            for idx, file in enumerate(sheet_files):
                row = idx // self.cols
                col = idx % self.cols

                if flip:
                    col = self.cols - 1 - col

                x = (self.x_offset + col * (self.settings.card_size.width +
                     self.settings.gap)) * mm
                y = (self.y_offset + row * (self.settings.card_size.height +
                     self.settings.gap)) * mm

                self._draw_card(c, file, x, y)

                if self.settings.crop_marks:
                    self._draw_crop_marks(c, x, y)

            c.showPage()

        c.save()

    def _generate_single_back(self, back_file: Path, count: int,
                             output: Path, title: str):
        """Генерация оборотной стороны с одним изображением"""
        logger.info(f"Генерация единого оборота для {count} визиток")

        page_width = self.settings.page_format.width * mm
        page_height = self.settings.page_format.height * mm

        c = canvas.Canvas(str(output), pagesize=(page_width, page_height))
        c.setTitle(title)

        cards_per_sheet = self.cols * self.rows
        total_sheets = (count + cards_per_sheet - 1) // cards_per_sheet

        for sheet_idx in range(total_sheets):
            start_idx = sheet_idx * cards_per_sheet
            remaining = min(cards_per_sheet, count - start_idx)

            for idx in range(remaining):
                row = idx // self.cols
                col = self.cols - 1 - (idx % self.cols)

                x = (self.x_offset + col * (self.settings.card_size.width +
                     self.settings.gap)) * mm
                y = (self.y_offset + row * (self.settings.card_size.height +
                     self.settings.gap)) * mm

                self._draw_card(c, back_file, x, y)

                if self.settings.crop_marks:
                    self._draw_crop_marks(c, x, y)

            c.showPage()

        c.save()

    def _draw_card(self, c: canvas.Canvas, image_path: Path, x: float, y: float):
        """Отрисовка одной визитки с улучшенной обработкой"""
        card_width = self.settings.card_size.width * mm
        card_height = self.settings.card_size.height * mm

        try:
            # Используем улучшенный процессор изображений
            target_size = (self.settings.card_size.width, self.settings.card_size.height)
            img_reader = ImageProcessor.process_image_for_print(
                image_path, self.settings, target_size
            )

            c.drawImage(img_reader, x, y, width=card_width, height=card_height,
                       preserveAspectRatio=True, mask='auto')

        except Exception as e:
            logger.error(f"Ошибка отрисовки визитки {image_path}: {e}")
            # Заглушка с ошибкой
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(x, y, card_width, card_height, fill=1)
            c.setFillColorRGB(1, 0, 0)
            c.setFont("Helvetica", 6)
            c.drawString(x + 2, y + card_height / 2, f"Error: {image_path.name}")

    def _draw_crop_marks(self, c: canvas.Canvas, x: float, y: float):
        """Отрисовка обрезных меток"""
        card_width = self.settings.card_size.width * mm
        card_height = self.settings.card_size.height * mm
        mark_len = self.settings.crop_mark_length * mm
        offset = self.settings.crop_mark_offset * mm

        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.25)

        # Левый нижний угол
        c.line(x - offset - mark_len, y, x - offset, y)
        c.line(x, y - offset - mark_len, x, y - offset)

        # Правый нижний угол
        c.line(x + card_width + offset, y, x + card_width + offset + mark_len, y)
        c.line(x + card_width, y - offset - mark_len, x + card_width, y - offset)

        # Левый верхний угол
        c.line(x - offset - mark_len, y + card_height, x - offset, y + card_height)
        c.line(x, y + card_height + offset, x, y + card_height + offset + mark_len)

        # Правый верхний угол
        c.line(x + card_width + offset, y + card_height,
               x + card_width + offset + mark_len, y + card_height)
        c.line(x + card_width, y + card_height + offset,
               x + card_width, y + card_height + offset + mark_len)

    def _merge_front_back(self, front_pdf: Path, back_pdf: Optional[Path],
                         output: Path):
        """Объединение лицевой и оборотной сторон"""
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

    def get_preview_data(self) -> Dict:
        """Получение данных для предпросмотра"""
        return {
            'cols': self.cols,
            'rows': self.rows,
            'cards_per_sheet': self.cols * self.rows,
            'card_width': self.settings.card_size.width,
            'card_height': self.settings.card_size.height,
            'page_width': self.settings.page_format.width,
            'page_height': self.settings.page_format.height,
            'x_offset': self.x_offset,
            'y_offset': self.y_offset,
            'gap': self.settings.gap
        }


class ImpositionApp:
    """Главный класс приложения"""

    def __init__(self):
        self.settings = PrintSettings(
            page_format=PageFormat.get_standard_formats()['A4'],
            card_size=CardSize.get_standard_sizes()['Standard RU']
        )
        self.logger = logging.getLogger(__name__)

    def process(self, front_cards: List[CardQuantity],
                back_cards: Optional[List[CardQuantity]],
                output_file: str) -> bool:
        """Основной процесс обработки"""
        self.logger.info(f"Начало обработки, выходной файл: {output_file}")

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generator = PDFGenerator(self.settings)
        success = generator.create_imposition(front_cards, back_cards, output_path)

        if success:
            self.logger.info(f"✅ PDF успешно создан: {output_path}")
        else:
            self.logger.error("❌ Ошибка при создании PDF")

        return success

    def save_config(self, config_file: str):
        """Сохранение конфигурации"""
        config = {
            'page_format': {
                'name': self.settings.page_format.name,
                'width': self.settings.page_format.width,
                'height': self.settings.page_format.height
            },
            'card_size': {
                'width': self.settings.card_size.width,
                'height': self.settings.card_size.height
            },
            'margins': {
                'top': self.settings.margin_top,
                'bottom': self.settings.margin_bottom,
                'left': self.settings.margin_left,
                'right': self.settings.margin_right
            },
            'bleed': self.settings.bleed,
            'gap': self.settings.gap,
            'crop_marks': self.settings.crop_marks,
            'dpi': self.settings.dpi,
            'output_dpi': self.settings.output_dpi,
            'color_mode': self.settings.color_mode.value,
            'matching_mode': self.settings.matching_mode.value,
            'strict_name_matching': self.settings.strict_name_matching
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Конфигурация сохранена: {config_file}")

    def load_config(self, config_file: str):
        """Загрузка конфигурации"""
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.settings.page_format = PageFormat(**config['page_format'])
        self.settings.card_size = CardSize(**config['card_size'])
        self.settings.margin_top = config['margins']['top']
        self.settings.margin_bottom = config['margins']['bottom']
        self.settings.margin_left = config['margins']['left']
        self.settings.margin_right = config['margins']['right']
        self.settings.bleed = config['bleed']
        self.settings.gap = config['gap']
        self.settings.crop_marks = config['crop_marks']
        self.settings.dpi = config.get('dpi', 300)
        self.settings.output_dpi = config.get('output_dpi', 300)
        self.settings.color_mode = ColorMode(config.get('color_mode', 'rgb'))
        self.settings.matching_mode = MatchingMode(config['matching_mode'])
        self.settings.strict_name_matching = config.get('strict_name_matching', True)

        self.logger.info(f"Конфигурация загружена: {config_file}")


if __name__ == "__main__":
    # Пример использования
    app = ImpositionApp()

    # Настройка параметров
    app.settings.page_format = PageFormat.get_standard_formats()['A4']
    app.settings.card_size = CardSize.get_standard_sizes()['Standard RU']
    app.settings.matching_mode = MatchingMode.ONE_TO_ONE
    app.settings.strict_name_matching = False
    app.settings.dpi = 300
    app.settings.color_mode = ColorMode.RGB

    # Создание списка визиток с количеством
    front_cards = [
        CardQuantity(Path("./input/front/card1.jpg"), 5),
        CardQuantity(Path("./input/front/card2.jpg"), 10),
    ]

    back_cards = [
        CardQuantity(Path("./input/back/card1.jpg"), 5),
        CardQuantity(Path("./input/back/card2.jpg"), 10),
    ]

    # Обработка
    app.process(
        front_cards=front_cards,
        back_cards=back_cards,
        output_file="./output/business_cards.pdf"
    )