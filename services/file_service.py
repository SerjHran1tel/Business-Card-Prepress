# -*- coding: utf-8 -*-
# services/file_service.py
import os
import aiofiles
import tempfile
from fastapi import UploadFile
from typing import List
from PIL import Image, ImageDraw, ImageFont
import random

from core.models import FileUploadResponse, DemoResponse
from utils.converter import convert_to_raster
from utils.helpers import sanitize_filename, ensure_directory


class FileService:
    def __init__(self):
        ensure_directory("temp/uploads")
        ensure_directory("temp/converted")
        ensure_directory("temp/output")

    async def process_uploaded_files(
            self,
            front_files: List[UploadFile],
            back_files: List[UploadFile]
    ) -> FileUploadResponse:
        """Обработка загруженных файлов"""
        try:
            front_paths = await self._save_files(front_files, "front")
            back_paths = await self._save_files(back_files, "back")

            # Конвертация векторных форматов
            converted_front, front_errors = await self._convert_files(front_paths)
            converted_back, back_errors = await self._convert_files(back_paths)

            all_errors = front_errors + back_errors

            return FileUploadResponse(
                success=True,
                message=f"Загружено {len(front_paths)} лицевых и {len(back_paths)} оборотных сторон",
                file_count=len(front_paths) + len(back_paths),
                front_files=converted_front,
                back_files=converted_back,
                converted_count=len([f for f in converted_front + converted_back if f not in front_paths + back_paths]),
                errors=all_errors
            )

        except Exception as e:
            return FileUploadResponse(
                success=False,
                message=f"Ошибка обработки файлов: {str(e)}",
                file_count=0,
                errors=[str(e)]
            )

    async def _save_files(self, files: List[UploadFile], file_type: str) -> List[str]:
        """Сохранение файлов на диск"""
        saved_paths = []

        for file in files:
            safe_filename = sanitize_filename(file.filename)
            file_path = os.path.join("temp", "uploads", f"{file_type}_{safe_filename}")

            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)

            saved_paths.append(file_path)

        return saved_paths

    async def _convert_files(self, file_paths: List[str]) -> tuple:
        """Конвертация файлов в растровый формат"""
        converted_paths = []
        errors = []

        for file_path in file_paths:
            try:
                new_path, error = await convert_to_raster(file_path)
                if error:
                    errors.append(f"{os.path.basename(file_path)}: {error}")
                converted_paths.append(new_path)
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        return converted_paths, errors

    async def generate_demo_files(self) -> DemoResponse:
        """Генерация демо-файлов"""
        try:
            front_files = []
            back_files = []

            # Создаем 4 демо-визитки
            for i in range(4):
                # Лицевая сторона
                front_img = Image.new('RGB', (900, 500), color=(
                    random.randint(50, 200),
                    random.randint(50, 200),
                    random.randint(50, 200)
                ))
                draw = ImageDraw.Draw(front_img)

                # Простой текст для демо
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    try:
                        font = ImageFont.load_default()
                    except:
                        font = None

                text = f"Демо Лицо {i + 1}"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (900 - text_width) // 2
                y = (500 - text_height) // 2

                draw.text((x, y), text, fill=(255, 255, 255), font=font)

                front_path = os.path.join("temp", "uploads", f"demo_front_{i + 1}.png")
                front_img.save(front_path, 'PNG', dpi=(300, 300))
                front_files.append(front_path)

                # Оборотная сторона
                back_img = Image.new('RGB', (900, 500), color=(
                    random.randint(50, 200),
                    random.randint(50, 200),
                    random.randint(50, 200)
                ))
                draw = ImageDraw.Draw(back_img)

                text = f"Демо Оборот {i + 1}"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (900 - text_width) // 2
                y = (500 - text_height) // 2

                draw.text((x, y), text, fill=(255, 255, 255), font=font)

                back_path = os.path.join("temp", "uploads", f"demo_back_{i + 1}.png")
                back_img.save(back_path, 'PNG', dpi=(300, 300))
                back_files.append(back_path)

            return DemoResponse(
                success=True,
                message="Демо-файлы успешно созданы",
                front_files=front_files,
                back_files=back_files
            )

        except Exception as e:
            return DemoResponse(
                success=False,
                message=f"Ошибка создания демо-файлов: {str(e)}",
                front_files=[],
                back_files=[]
            )