# -*- coding: utf-8 -*-
# core/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


@dataclass
class Party:
    front_images: List[str]
    back_images: List[str]
    quantity: int
    name: str = ""

    @property
    def total_cards(self):
        return len(self.front_images) * self.quantity


@dataclass
class LayoutResult:
    cards_x: int
    cards_y: int
    cards_total: int
    positions: List[Dict[str, float]]
    rotated: bool
    efficiency: float


# Pydantic модели для API
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_count: int
    front_files: List[str] = field(default_factory=list)
    back_files: List[str] = field(default_factory=list)
    converted_count: int = 0
    errors: List[str] = field(default_factory=list)


class ValidationRequest(BaseModel):
    front_files: List[str]
    back_files: List[str]
    scheme: str = '1:1'
    match_by_name: bool = False
    card_width: int = 90
    card_height: int = 50
    bleed: int = 3


class ValidationResponse(BaseModel):
    success: bool
    report: str
    errors: List[str]
    warnings: List[str]
    infos: List[str]


class LayoutRequest(BaseModel):
    sheet_width: int
    sheet_height: int
    card_width: int
    card_height: int
    margin: int
    bleed: int
    gutter: int
    rotate: bool = False


class LayoutResponse(BaseModel):
    success: bool
    layout: Dict[str, Any]
    error: str = ""


class PDFGenerationRequest(BaseModel):
    parties: List[Dict[str, Any]]
    config: Dict[str, Any]
    output_filename: str = "business_cards.pdf"


class PDFGenerationResponse(BaseModel):
    success: bool
    message: str
    download_url: str
    file_size: int
    total_sheets: int
    total_cards: int


class PartyRequest(BaseModel):
    front_files: List[str]
    back_files: List[str]
    quantity: int
    name: str = ""


class DemoResponse(BaseModel):
    success: bool
    message: str
    front_files: List[str]
    back_files: List[str]