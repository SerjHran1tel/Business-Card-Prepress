# -*- coding: utf-8 -*-
# api/endpoints.py
import os
import shutil
import logging
from typing import List
import tempfile
import time

import aiofiles
from PIL import Image
import fitz  # PyMuPDF
import cairosvg
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from io import BytesIO
import base64

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from core.models import LayoutResult, Party, ValidationResponse, LayoutResponse, PDFGenerationResponse, \
    FileUploadResponse, DemoResponse, PDFGenerationRequest, LayoutRequest, ValidationRequest
from core.config import PrintConfig
from core.exceptions import FileProcessingError, ValidationError, LayoutCalculationError, PDFGenerationError
from layout_calculator import LayoutCalculator
from pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

# Создаем роутер
api_router = APIRouter()

class FileService:
    async def process_uploaded_files(self, front_files: List[UploadFile], back_files: List[UploadFile], dpi: int = 300) -> tuple[List[str], List[str], int, List[str]]:
        front_paths = []
        back_paths = []
        converted_count = 0
        errors = []

        os.makedirs("temp/uploads", exist_ok=True)
        os.makedirs("temp/converted", exist_ok=True)

        for is_front, files in ((True, front_files or []), (False, back_files or [])):
            for file in files:
                original_filename = file.filename
                ext = os.path.splitext(original_filename)[1].lower()
                upload_path = os.path.join("temp/uploads", original_filename)

                try:
                    async with aiofiles.open(upload_path, 'wb') as f:
                        content = await file.read()
                        await f.write(content)

                    path = upload_path
                    if ext in ['.pdf', '.svg']:
                        converted_path = os.path.join("temp/converted", os.path.splitext(original_filename)[0] + '.png')
                        if ext == '.svg':
                            cairosvg.svg2png(url=upload_path, write_to=converted_path, dpi=dpi)
                        elif ext == '.pdf':
                            doc = fitz.open(upload_path)
                            if len(doc) > 0:
                                page = doc[0]
                                pix = page.get_pixmap(dpi=dpi)
                                pix.save(converted_path)
                            doc.close()
                        path = converted_path
                        converted_count += 1

                    if is_front:
                        front_paths.append(path)
                    else:
                        back_paths.append(path)
                except Exception as e:
                    errors.append(f"Ошибка обработки {original_filename}: {str(e)}")
                    logger.error(f"Ошибка обработки файла: {e}")

        if errors:
            raise FileProcessingError(f"Ошибки при обработке файлов: {', '.join(errors)}")

        return front_paths, back_paths, converted_count, errors

class ValidationService:
    async def validate_images(self, front_paths: List[str], back_paths: List[str], scheme: str = '1:1', match_by_name: bool = False,
                              card_width: int = 90, card_height: int = 50, bleed: int = 3, dpi: int = 300) -> ValidationResponse:
        errors = []
        warnings = []
        infos = []

        # Проверяем, что хотя бы одна сторона предоставлена
        if not front_paths and not back_paths:
            errors.append("Не предоставлены ни лицевые, ни оборотные изображения")
            report = "\n".join(infos + warnings + errors)
            raise ValidationError("Валидация не пройдена: отсутствуют изображения")

        # Логируем случай односторонней печати
        if not front_paths:
            infos.append("Лицевые изображения отсутствуют, будет использоваться только оборотная сторона")
        elif not back_paths:
            infos.append("Оборотные изображения отсутствуют, будет использоваться только лицевая сторона")

        # Проверка парного соответствия только если обе стороны предоставлены
        if front_paths and back_paths and match_by_name:
            front_dict = {os.path.splitext(os.path.basename(p))[0]: p for p in front_paths}
            back_dict = {os.path.splitext(os.path.basename(p))[0]: p for p in back_paths}
            matched_front = []
            matched_back = []
            for name, fpath in front_dict.items():
                if name in back_dict:
                    matched_front.append(fpath)
                    matched_back.append(back_dict[name])
                else:
                    warnings.append(f"Нет парного оборота для лицевой стороны: {name}")
            for name in set(back_dict) - set(front_dict):
                warnings.append(f"Нет парной лицевой стороны для оборота: {name}")
            front_paths = matched_front
            back_paths = matched_back

        # Проверка количества для схемы 1:1 только если обе стороны есть
        if front_paths and back_paths and scheme == '1:1':
            if len(front_paths) != len(back_paths):
                errors.append(f"Несоответствие количества лицевых и оборотных сторон для схемы 1:1: {len(front_paths)} vs {len(back_paths)}")
        elif back_paths and scheme == '1:N' and len(back_paths) != 1:
            errors.append(f"Ожидается ровно 1 оборотное изображение для схемы 1:N, получено {len(back_paths)}")

        # Проверка размеров изображений
        target_w_px = int((card_width + 2 * bleed) * dpi / 25.4)
        target_h_px = int((card_height + 2 * bleed) * dpi / 25.4)
        for paths, side in ((front_paths, "лицевая"), (back_paths, "оборотная")):
            for p in paths:
                try:
                    img = Image.open(p)
                    if img.width != target_w_px or img.height != target_h_px:
                        warnings.append(f"{side.capitalize()} изображение {os.path.basename(p)} размер {img.width}x{img.height} != целевой {target_w_px}x{target_h_px}")
                except Exception as e:
                    errors.append(f"Не удалось открыть {side} изображение {p}: {str(e)}")

        report = "\n".join(infos + warnings + errors)
        if errors:
            raise ValidationError("Валидация не пройдена")

        return ValidationResponse(
            success=len(errors) == 0,
            report=report,
            errors=errors,
            warnings=warnings,
            infos=infos
        )

class LayoutService:
    async def calculate_layout(self, sheet_width: int, sheet_height: int, card_width: int, card_height: int,
                              margin: int, bleed: int, gutter: int, rotate: bool = False) -> LayoutResponse:
        try:
            calculator = LayoutCalculator(sheet_width, sheet_height, card_width, card_height, margin, bleed, gutter, rotate)
            layout = calculator.calculate_layout()
            if layout.cards_total == 0:
                raise LayoutCalculationError("Не найдена подходящая раскладка")
            return LayoutResponse(success=True, layout=layout.__dict__)
        except Exception as e:
            logger.error(f"Ошибка расчета раскладки: {e}")
            raise LayoutCalculationError(str(e))

class PDFService:
    async def generate_pdf(self, parties: List[dict], config_dict: dict, output_filename: str, background_tasks: BackgroundTasks) -> PDFGenerationResponse:
        try:
            # Приведение config_dict к параметрам PrintConfig
            config_params = {
                'sheet_size': config_dict.get('sheet_size', 'A4'),
                'custom_sheet': config_dict.get('custom_sheet', False),
                'custom_sheet_width': config_dict.get('sheet_width', 210),
                'custom_sheet_height': config_dict.get('sheet_height', 297),
                'card_size': config_dict.get('card_size', 'Стандартная (90×50)'),
                'custom_card_width': config_dict.get('card_width', 90),
                'custom_card_height': config_dict.get('card_height', 50),
                'margin': config_dict.get('margin', 5),
                'bleed': config_dict.get('bleed', 3),
                'gutter': config_dict.get('gutter', 2),
                'rotate_cards': config_dict.get('rotate_cards', False),
                'add_crop_marks': config_dict.get('add_crop_marks', True),
                'mark_length': config_dict.get('mark_length', 5),
                'mark_thickness': config_dict.get('mark_thickness', 0.3),
                'matching_scheme': config_dict.get('matching_scheme', '1:1'),
                'fit_proportions': config_dict.get('fit_proportions', True),
                'match_by_name': config_dict.get('match_by_name', False),
                'dpi': config_dict.get('dpi', 300)
            }
            config = PrintConfig(**config_params)
            all_fronts = []
            all_backs = []
            for party in parties:
                fronts = party['front_images']
                backs = party['back_images']
                qty = party['quantity']
                if fronts:
                    all_fronts.extend(fronts * qty)
                if backs:
                    if config.matching_scheme == '1:1' and fronts:
                        all_backs.extend(backs * qty)
                    elif config.matching_scheme == '1:N':
                        all_backs.extend([backs[0]] * (len(fronts) * qty if fronts else qty))
                    elif config.matching_scheme == 'M:N':
                        cycle_len = len(backs)
                        all_backs.extend(backs[i % cycle_len] for i in range(len(fronts) * qty if fronts else qty))

            if not all_fronts and not all_backs:
                raise PDFGenerationError("Не предоставлены ни лицевые, ни оборотные изображения")

            output_path = os.path.join("temp/output", output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            generator = PDFGenerator(config)
            stats = generator.generate_pdf(all_fronts, all_backs, output_path)
            background_tasks.add_task(cleanup_file, output_path)
            file_size = os.path.getsize(output_path)
            return PDFGenerationResponse(
                success=True,
                message="PDF успешно сгенерирован",
                download_url=f"/api/v1/download/{output_filename}",
                file_size=file_size,
                total_sheets=stats['total_sheets'],
                total_cards=stats['total_cards']
            )
        except Exception as e:
            logger.error(f"Ошибка генерации PDF: {e}")
            raise PDFGenerationError(str(e))

    async def generate_preview(self, front_images: List[str], back_images: List[str], config_dict: dict) -> JSONResponse:
        try:
            # Приведение config_dict к параметрам PrintConfig
            config_params = {
                'sheet_size': config_dict.get('sheet_size', 'A4'),
                'custom_sheet': config_dict.get('custom_sheet', False),
                'custom_sheet_width': config_dict.get('sheet_width', 210),
                'custom_sheet_height': config_dict.get('sheet_height', 297),
                'card_size': config_dict.get('card_size', 'Стандартная (90×50)'),
                'custom_card_width': config_dict.get('card_width', 90),
                'custom_card_height': config_dict.get('card_height', 50),
                'margin': config_dict.get('margin', 5),
                'bleed': config_dict.get('bleed', 3),
                'gutter': config_dict.get('gutter', 2),
                'rotate_cards': config_dict.get('rotate_cards', False),
                'add_crop_marks': config_dict.get('add_crop_marks', True),
                'mark_length': config_dict.get('mark_length', 5),
                'mark_thickness': config_dict.get('mark_thickness', 0.3),
                'matching_scheme': config_dict.get('matching_scheme', '1:1'),
                'fit_proportions': config_dict.get('fit_proportions', True),
                'match_by_name': config_dict.get('match_by_name', False),
                'dpi': config_dict.get('dpi', 300)
            }
            config = PrintConfig(**config_params)
            sheet_width, sheet_height = config.get_sheet_dimensions()
            card_width, card_height = config.get_card_dimensions()
            calculator = LayoutCalculator(
                sheet_width, sheet_height, card_width, card_height,
                config.margin, config.bleed, config.gutter, config.rotate_cards
            )
            layout = calculator.calculate_layout()
            if layout.cards_total == 0:
                raise LayoutCalculationError("Не найдена подходящая раскладка для предпросмотра")

            # Выбираем сторону для предпросмотра (лицевая предпочтительнее, если есть)
            images = front_images[:layout.cards_total] if front_images else back_images[:layout.cards_total]
            side_type = "front" if front_images else "back"
            if not images:
                raise LayoutCalculationError("Нет изображений для предпросмотра")

            # Создаем временный PDF для первого листа
            temp_pdf = os.path.join("temp/output", f"preview_{int(time.time())}.pdf")
            c = canvas.Canvas(temp_pdf, pagesize=(sheet_width * mm, sheet_height * mm))
            generator = PDFGenerator(config)
            generator._generate_side(c, images, layout, side_type)
            c.save()

            # Конвертируем PDF в PNG
            doc = fitz.open(temp_pdf)
            page = doc[0]
            pix = page.get_pixmap(dpi=config.dpi)
            img_data = pix.tobytes("png")
            doc.close()
            os.unlink(temp_pdf)

            # Кодируем изображение в base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            return JSONResponse({
                "success": True,
                "preview_image": f"data:image/png;base64,{img_base64}",
                "layout": layout.__dict__,
                "side": side_type
            })
        except Exception as e:
            logger.error(f"Ошибка генерации предпросмотра: {e}")
            raise HTTPException(500, f"Ошибка генерации предпросмотра: {str(e)}")

# Инстансы сервисов
file_service = FileService()
validation_service = ValidationService()
layout_service = LayoutService()
pdf_service = PDFService()

@api_router.post("/upload", response_model=FileUploadResponse)
async def upload_files(
        front_files: List[UploadFile] = File(None),
        back_files: List[UploadFile] = File(None)
):
    try:
        front_paths, back_paths, converted_count, errors = await file_service.process_uploaded_files(front_files, back_files)
        return FileUploadResponse(
            success=not errors,
            message="Файлы загружены и обработаны" if not errors else "Произошли ошибки при обработке",
            file_count=len(front_paths) + len(back_paths),
            front_files=front_paths,
            back_files=back_paths,
            converted_count=converted_count,
            errors=errors
        )
    except FileProcessingError as e:
        raise HTTPException(400, str(e))

@api_router.post("/validate", response_model=ValidationResponse)
async def validate_images(request: ValidationRequest):
    try:
        return await validation_service.validate_images(
            request.front_files, request.back_files, request.scheme, request.match_by_name,
            request.card_width, request.card_height, request.bleed
        )
    except ValidationError as e:
        raise HTTPException(400, str(e))

@api_router.post("/calculate-layout", response_model=LayoutResponse)
async def calculate_layout(request: LayoutRequest):
    try:
        return await layout_service.calculate_layout(
            request.sheet_width, request.sheet_height, request.card_width, request.card_height,
            request.margin, request.bleed, request.gutter, request.rotate
        )
    except LayoutCalculationError as e:
        return LayoutResponse(success=False, layout={}, error=str(e))

@api_router.post("/generate-pdf", response_model=PDFGenerationResponse)
async def generate_pdf(
        request: PDFGenerationRequest,
        background_tasks: BackgroundTasks
):
    try:
        return await pdf_service.generate_pdf(request.parties, request.config, request.output_filename, background_tasks)
    except PDFGenerationError as e:
        raise HTTPException(500, str(e))

@api_router.post("/preview")
async def generate_preview(request: PDFGenerationRequest):
    try:
        # Используем изображения только первой партии для предпросмотра
        front_images = request.parties[0]['front_images'] if request.parties else []
        back_images = request.parties[0]['back_images'] if request.parties and request.parties[0]['back_images'] else []
        return await pdf_service.generate_preview(front_images, back_images, request.config)
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации предпросмотра: {str(e)}")

@api_router.get("/demo", response_model=DemoResponse)
async def generate_demo_files():
    return DemoResponse(
        success=True,
        message="Демо-файлы сгенерированы (заглушка)",
        front_files=["demo_front1.png", "demo_front2.png"],
        back_files=["demo_back1.png"]
    )

@api_router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("temp/output", filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "Файл не найден")
    return FileResponse(file_path, media_type='application/pdf', filename=filename)

@api_router.delete("/clear-temp")
async def clear_temp_files():
    try:
        for folder in ["uploads", "converted", "output"]:
            folder_path = os.path.join("temp", folder)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                os.makedirs(folder_path)
        return JSONResponse({"success": True, "message": "Временные файлы очищены"})
    except Exception as e:
        raise HTTPException(500, f"Ошибка очистки: {str(e)}")

@api_router.get("/supported-formats")
async def get_supported_formats():
    return JSONResponse({
        "raster": ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp'],
        "vector": ['.pdf', '.svg'],
        "max_size": "100MB"
    })

@api_router.get("/dependencies")
async def check_dependencies():
    dependencies = {}
    missing = []
    try:
        import fitz
        dependencies["PyMuPDF"] = "Установлен"
    except ImportError:
        missing.append("PyMuPDF")
    try:
        import cairosvg
        dependencies["CairoSVG"] = "Установлен"
    except ImportError:
        missing.append("CairoSVG")
    return JSONResponse({"dependencies": dependencies, "missing_tools": missing})

def cleanup_file(file_path: str):
    time.sleep(300)  # 5 минут
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Ошибка очистки файла {file_path}: {e}")