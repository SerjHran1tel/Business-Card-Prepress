"""
Управление файлами и валидация
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PIL import Image
from .models import ValidationResult, MatchingMode

logger = logging.getLogger(__name__)


class FileManager:
    SUPPORTED_FORMATS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.eps'}

    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, str]:
        try:
            if not file_path.exists():
                return False, "Файл не существует"

            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, "Файл пустой"
            if file_size > 100 * 1024 * 1024:
                return False, "Файл слишком большой (>100MB)"

            if file_path.suffix.lower() not in FileManager.SUPPORTED_FORMATS:
                return False, f"Неподдерживаемый формат: {file_path.suffix}"

            if file_path.suffix.lower() == '.pdf':
                try:
                    import fitz
                    doc = fitz.open(str(file_path))
                    if len(doc) == 0:
                        return False, "PDF файл поврежден"
                    doc.close()
                except Exception as e:
                    return False, f"Ошибка чтения PDF: {str(e)}"
            else:
                try:
                    with Image.open(file_path) as img:
                        img.verify()
                except Exception as e:
                    return False, f"Изображение повреждено: {str(e)}"

            return True, "OK"
        except Exception as e:
            return False, f"Ошибка валидации: {str(e)}"

    @staticmethod
    def scan_directory(directory: Path) -> List[Path]:
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
        name = Path(filename).stem.lower()
        name = re.sub(r'[^\w]', '', name)
        return name

    @staticmethod
    def match_files(front_files: List[Path], back_files: List[Path],
                   strict: bool = True) -> Dict[Path, Optional[Path]]:
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
        result = ValidationResult()

        if not front_dir.exists():
            result.add_error(f"Директория лицевых сторон не найдена: {front_dir}")
            return result

        front_files = FileManager.scan_directory(front_dir)
        if not front_files:
            result.add_error(f"Не найдено файлов в директории: {front_dir}")
            return result

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

            for file in back_files:
                is_valid, message = FileManager.validate_file(file)
                if not is_valid:
                    result.add_error(f"Оборотная сторона {file.name}: {message}")

            matches = FileManager.match_files(front_files, back_files, strict_matching)

            missing_backs = [f.name for f, b in matches.items() if b is None]
            if missing_backs and strict_matching:
                result.add_warning(
                    f"Отсутствуют оборотные стороны для: {', '.join(missing_backs)}"
                )

        elif matching_mode == MatchingMode.ONE_TO_MANY:
            if back_dir.exists():
                back_files = FileManager.scan_directory(back_dir)
                if len(back_files) != 1:
                    result.add_error(
                        f"В режиме ONE_TO_MANY должен быть ровно 1 файл оборота"
                    )

        return result