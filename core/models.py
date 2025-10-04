"""
Data classes и Enum для системы импозиции
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
from pathlib import Path


class Orientation(Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


class MatchingMode(Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class ColorMode(Enum):
    RGB = "rgb"
    CMYK = "cmyk"


@dataclass
class PageFormat:
    name: str
    width: float
    height: float

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
    width: float
    height: float

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
    file_path: Path
    quantity: int = 1


@dataclass
class PrintSettings:
    page_format: PageFormat
    card_size: CardSize
    margin_top: float = 10.0
    margin_bottom: float = 10.0
    margin_left: float = 10.0
    margin_right: float = 10.0
    bleed: float = 3.0
    gap: float = 2.0
    crop_marks: bool = True
    crop_mark_length: float = 5.0
    crop_mark_offset: float = 2.0
    orientation: Orientation = Orientation.AUTO
    matching_mode: MatchingMode = MatchingMode.ONE_TO_ONE
    strict_name_matching: bool = True
    dpi: int = 300
    color_mode: ColorMode = ColorMode.RGB
    output_dpi: int = 300


class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)

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