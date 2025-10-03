# -*- coding: utf-8 -*-
# services/validation_service.py
from utils.image_utils import (
    validate_image_pairs_extended,
    generate_validation_report,
    get_image_info
)
from core.models import ValidationRequest, ValidationResponse


class ValidationService:
    async def validate_images(self, request: ValidationRequest) -> ValidationResponse:
        """Валидация изображений"""
        try:
            front_infos = []
            for path in request.front_files:
                info = get_image_info(path)
                front_infos.append(info)

            back_infos = []
            for path in request.back_files:
                info = get_image_info(path)
                back_infos.append(info)

            validation_result = validate_image_pairs_extended(
                front_infos, back_infos,
                request.scheme, request.match_by_name,
                request.card_width, request.card_height, request.bleed
            )

            report = generate_validation_report(validation_result)

            return ValidationResponse(
                success=True,
                report=report,
                errors=validation_result.errors,
                warnings=validation_result.warnings,
                infos=validation_result.infos
            )

        except Exception as e:
            return ValidationResponse(
                success=False,
                report=f"Ошибка валидации: {str(e)}",
                errors=[str(e)],
                warnings=[],
                infos=[]
            )