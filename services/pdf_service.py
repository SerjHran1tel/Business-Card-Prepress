# -*- coding: utf-8 -*-
# services/pdf_service.py
import os
from fastapi import BackgroundTasks
from pdf_generator import PDFGenerator
from core.config import PrintConfig
from core.models import PDFGenerationRequest, PDFGenerationResponse


class PDFService:
    async def generate_pdf(
            self,
            request: PDFGenerationRequest,
            background_tasks: BackgroundTasks
    ) -> PDFGenerationResponse:
        """Генерация PDF файла"""
        try:
            # Создаем конфиг из запроса
            config_data = request.config
            config = PrintConfig(**config_data)

            # Собираем все изображения из партий
            all_front = []
            all_back = []

            for party in request.parties:
                for _ in range(party['quantity']):
                    all_front.extend(party['front_images'])
                    if party['back_images']:
                        if config.matching_scheme == '1:1':
                            all_back.extend(party['back_images'])
                        elif config.matching_scheme == '1:N':
                            all_back.extend([party['back_images'][0]] * len(party['front_images']))
                        elif config.matching_scheme == 'M:N':
                            all_back.extend([
                                party['back_images'][i % len(party['back_images'])]
                                for i in range(len(party['front_images']))
                            ])

            # Генерируем PDF
            generator = PDFGenerator(config)
            output_path = os.path.join("temp", "output", request.output_filename)

            result = generator.generate_pdf(all_front, all_back, output_path)

            # Добавляем задачу очистки
            background_tasks.add_task(self._cleanup_file, output_path)

            file_size = os.path.getsize(output_path)

            return PDFGenerationResponse(
                success=True,
                message="PDF успешно сгенерирован",
                download_url=f"/api/v1/download/{request.output_filename}",
                file_size=file_size,
                total_sheets=result['total_sheets'],
                total_cards=result['total_cards']
            )

        except Exception as e:
            return PDFGenerationResponse(
                success=False,
                message=f"Ошибка генерации PDF: {str(e)}",
                download_url="",
                file_size=0,
                total_sheets=0,
                total_cards=0
            )

    def _cleanup_file(self, file_path: str):
        """Очистка временного файла"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            pass