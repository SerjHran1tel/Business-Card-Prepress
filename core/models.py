# -*- coding: utf-8 -*-
# core/models.py
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ImageInfo:
    path: str
    filename: str
    size: Tuple[int, int]
    format: Optional[str] = None
    mode: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Party:
    front_images: List[str]
    back_images: List[str]
    quantity: int

    @property
    def total_cards(self) -> int:
        return len(self.front_images) * self.quantity


@dataclass
class LayoutResult:
    cards_x: int
    cards_y: int
    cards_total: int
    positions: List[dict]
    rotated: bool
    efficiency: float


@dataclass
class PDFGenerationResult:
    total_sheets: int
    cards_per_sheet: int
    total_cards: int
    output_path: str