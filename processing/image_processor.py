"""
Обработка изображений для печати
"""
import logging
from pathlib import Path
from typing import Tuple
from io import BytesIO

from PIL import Image, ImageCms
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)


class ImageProcessor:
    @staticmethod
    def convert_to_cmyk(image: Image.Image) -> Image.Image:
        try:
            cmyk_profile = ImageCms.createProfile("sRGB")
            return ImageCms.profileToProfile(image, cmyk_profile, cmyk_profile, outputMode='CMYK')
        except Exception as e:
            logger.warning(f"Не удалось конвертировать в CMYK: {e}")
            return image.convert('CMYK')

    @staticmethod
    def process_image_for_print(image_path: Path, settings,
                               target_size: Tuple[float, float]) -> ImageReader:
        try:
            if image_path.suffix.lower() == '.pdf':
                try:
                    from pdf2image import convert_from_path
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
                except ImportError:
                    raise Exception("PDF поддержка не установлена")
            else:
                img = Image.open(image_path)

            if settings.color_mode.value == 'cmyk':
                img = ImageProcessor.convert_to_cmyk(img)

            target_width_px = int(target_size[0] * settings.dpi / 25.4)
            target_height_px = int(target_size[1] * settings.dpi / 25.4)

            img.thumbnail((target_width_px, target_height_px), Image.Resampling.LANCZOS)

            buffer = BytesIO()
            if settings.color_mode.value == 'cmyk':
                img.save(buffer, format='TIFF', dpi=(settings.dpi, settings.dpi))
            else:
                img.save(buffer, format='PNG', dpi=(settings.dpi, settings.dpi))

            buffer.seek(0)
            return ImageReader(buffer)

        except Exception as e:
            logger.error(f"Ошибка обработки изображения {image_path}: {e}")
            buffer = BytesIO()
            placeholder = Image.new('RGB', (100, 100), color='lightgray')
            placeholder.save(buffer, format='PNG')
            buffer.seek(0)
            return ImageReader(buffer)

    @staticmethod
    def create_preview(image_path: Path, max_size=(200, 200)) -> str | None:
        try:
            if image_path.suffix.lower() == '.pdf':
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(str(image_path), first_page=1, last_page=1, dpi=100)
                    if images:
                        img = images[0]
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        buffer = BytesIO()
                        img.save(buffer, format='PNG')
                        import base64
                        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
                except ImportError:
                    pass
                return None
            else:
                img = Image.open(image_path)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                import base64
                return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        except Exception as e:
            logger.error(f"Ошибка создания превью {image_path}: {e}")
            return None