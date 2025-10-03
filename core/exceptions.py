# -*- coding: utf-8 -*-
# core/exceptions.py
class BusinessCardException(Exception):
    """Базовое исключение приложения"""
    pass

class FileProcessingError(BusinessCardException):
    """Ошибка обработки файла"""
    pass

class LayoutCalculationError(BusinessCardException):
    """Ошибка расчета раскладки"""
    pass

class PDFGenerationError(BusinessCardException):
    """Ошибка генерации PDF"""
    pass

class ValidationError(BusinessCardException):
    """Ошибка валидации"""
    pass