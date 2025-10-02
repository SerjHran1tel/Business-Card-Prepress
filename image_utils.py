# -*- coding: utf-8 -*-
# image_utils.py
from PIL import Image, ImageCms
import os
import math
import io
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class ValidationResult:
    errors: List[str]
    warnings: List[str]
    infos: List[str]
    dpi_issues: List[str]
    color_issues: List[str]
    safe_zone_issues: List[str]


SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp')


def get_image_info(filepath):
    """Получить информацию об изображении"""
    try:
        with Image.open(filepath) as img:
            info = {
                'filename': os.path.basename(filepath),
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'path': filepath
            }

            # Добавляем информацию о DPI
            if 'dpi' in img.info:
                info['dpi'] = img.info['dpi']
            else:
                info['dpi'] = (72, 72)  # Default

            # Проверяем цветовой профиль
            try:
                icc_profile = img.info.get('icc_profile')
                if icc_profile:
                    info['color_profile'] = 'ICC'
                    # Проверяем тип профиля
                    try:
                        profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
                        info['color_space'] = ImageCms.getProfileName(profile).upper()
                    except:
                        info['color_space'] = 'UNKNOWN'
                else:
                    info['color_profile'] = 'None'
                    info['color_space'] = img.mode
            except Exception:
                info['color_profile'] = 'Unknown'
                info['color_space'] = img.mode

            return info
    except Exception as e:
        return {
            'filename': os.path.basename(filepath),
            'error': str(e),
            'path': filepath
        }


def scan_images(file_list_or_folder, scan_folder=False):
    """Просканировать список файлов или папку изображений"""
    if not file_list_or_folder:
        return [], []

    infos = []
    errors = []

    if scan_folder:
        # Рекурсивное сканирование папки
        for root, dirs, files in os.walk(file_list_or_folder):
            for f in files:
                filepath = os.path.join(root, f)
                if filepath.lower().endswith(SUPPORTED_FORMATS):
                    info = get_image_info(filepath)
                    if 'error' in info:
                        errors.append(info)
                    else:
                        infos.append(info)
    else:
        # Список файлов
        for f in file_list_or_folder:
            if not os.path.exists(f) or not f.lower().endswith(SUPPORTED_FORMATS):
                errors.append({
                    'filename': os.path.basename(f),
                    'error': 'Файл не существует или неподдерживаемый формат',
                    'path': f
                })
                continue
            info = get_image_info(f)
            if 'error' in info:
                errors.append(info)
            else:
                infos.append(info)

    return infos, errors


def check_dpi_compliance(image_info, min_dpi=300):
    """Проверить соответствие DPI требованиям"""
    issues = []
    dpi_x, dpi_y = image_info.get('dpi', (72, 72))
    min_dpi_actual = min(dpi_x, dpi_y)

    if min_dpi_actual < min_dpi:
        physical_width = (image_info['size'][0] / min_dpi_actual) * 25.4
        physical_height = (image_info['size'][1] / min_dpi_actual) * 25.4
        recommended_width = math.ceil((image_info['size'][0] / min_dpi_actual) * min_dpi)
        recommended_height = math.ceil((image_info['size'][1] / min_dpi_actual) * min_dpi)

        issues.append(
            f"Низкое разрешение: {min_dpi_actual} DPI (требуется {min_dpi}+). "
            f"Физический размер: {physical_width:.1f}×{physical_height:.1f} мм. "
            f"Рекомендуется: {recommended_width}×{recommended_height} пикселей"
        )

    return issues


def check_color_profile(image_info):
    """Проверить цветовой профиль"""
    issues = []
    color_space = image_info.get('color_space', '').upper()
    mode = image_info.get('mode', '').upper()

    if 'CMYK' in color_space:
        issues.append("Изображение в CMYK - может потребоваться конвертация в RGB для печати")
    elif mode == 'CMYK':
        issues.append("Режим CMYK - может потребоваться конвертация в RGB")
    elif 'RGB' not in color_space and mode != 'RGB':
        issues.append(f"Цветовое пространство: {color_space} - рекомендуется RGB")

    if not image_info.get('color_profile') or image_info.get('color_profile') == 'None':
        issues.append("Отсутствует цветовой профиль")

    return issues


def validate_image_pairs(front_infos, back_infos, scheme='1:1', match_by_name=False):
    """Базовая проверка соответствия лицевых и оборотных сторон"""
    errors = []
    warnings = []

    front_count = len(front_infos)
    back_count = len(back_infos)

    if front_count == 0:
        errors.append("Не найдено лицевых сторон")

    # Проверяем соответствие по количеству
    if scheme == '1:1' and front_count != back_count and back_count > 0:
        warnings.append(f"Несоответствие количества: {front_count} лиц vs {back_count} рубашек")

    # Если match_by_name, сортируем по имени и проверяем совпадения
    if match_by_name and scheme == '1:1' and front_count == back_count:
        front_names = sorted([os.path.splitext(info['filename'])[0] for info in front_infos])
        back_names = sorted([os.path.splitext(info['filename'])[0] for info in back_infos])
        mismatches = [i for i, (f, b) in enumerate(zip(front_names, back_names)) if f != b]
        if mismatches:
            warnings.append(f"Несовпадения имен: {len(mismatches)} пар (файлы отсортированы по имени)")

    # Проверяем размеры изображений
    min_len = min(front_count, back_count if scheme == '1:1' else front_count)
    for i in range(min_len):
        front = front_infos[i]
        if 'size' not in front:
            errors.append(f"Невалидный файл лицевой стороны: {front['filename']}")
            continue
        if scheme == '1:1' and i < back_count:
            back = back_infos[i]
            if 'size' not in back:
                errors.append(f"Невалидный файл оборотной стороны: {back['filename']}")
                continue
            if front['size'] != back['size']:
                warnings.append(f"Разный размер: {front['filename']} vs {back['filename']}")

    return errors, warnings


def validate_image_pairs_extended(front_infos, back_infos, scheme='1:1', match_by_name=False,
                                  card_width=90, card_height=50, bleed=3, min_dpi=300):
    """Расширенная проверка соответствия лицевых и оборотных сторон"""
    result = ValidationResult([], [], [], [], [], [])

    front_count = len(front_infos)
    back_count = len(back_infos)

    if front_count == 0:
        result.errors.append("Не найдено лицевых сторон")

    # Проверяем соответствие по количеству для разных схем
    if scheme == '1:1' and front_count != back_count and back_count > 0:
        result.warnings.append(f"Несоответствие количества: {front_count} лиц vs {back_count} рубашек")
    elif scheme == '1:N' and back_count == 0:
        result.errors.append("Для схемы 1:N требуется хотя бы одна оборотная сторона")
    elif scheme == 'M:N' and (front_count == 0 or back_count == 0):
        result.errors.append("Для схемы M:N требуются и лицевые и оборотные стороны")

    # Проверка DPI и цветовых профилей для всех изображений
    all_images = front_infos + back_infos
    for img_info in all_images:
        if 'error' in img_info:
            result.errors.append(f"Ошибка загрузки {img_info['filename']}: {img_info['error']}")
            continue

        # Проверка DPI
        dpi_issues = check_dpi_compliance(img_info, min_dpi)
        result.dpi_issues.extend([f"{img_info['filename']}: {issue}" for issue in dpi_issues])

        # Проверка цветовых профилей
        color_issues = check_color_profile(img_info)
        result.color_issues.extend([f"{img_info['filename']}: {issue}" for issue in color_issues])

        # Проверка безопасной зоны
        safe_zone_issues = check_safe_zone_compliance(img_info, card_width, card_height, bleed)
        result.safe_zone_issues.extend([f"{img_info['filename']}: {issue}" for issue in safe_zone_issues])

    # Если match_by_name, сортируем по имени и проверяем совпадения
    if match_by_name and scheme == '1:1' and front_count == back_count:
        front_names = sorted([os.path.splitext(info['filename'])[0] for info in front_infos])
        back_names = sorted([os.path.splitext(info['filename'])[0] for info in back_infos])
        mismatches = [i for i, (f, b) in enumerate(zip(front_names, back_names)) if f != b]
        if mismatches:
            result.warnings.append(f"Несовпадения имен: {len(mismatches)} пар")

    # Строгая валидация для схемы M:N
    if scheme == 'M:N' and front_count > 0 and back_count > 0:
        front_ratios = [info['size'][0] / info['size'][1] for info in front_infos if 'size' in info]
        back_ratios = [info['size'][0] / info['size'][1] for info in back_infos if 'size' in info]

        if front_ratios and back_ratios:
            avg_front_ratio = sum(front_ratios) / len(front_ratios)
            avg_back_ratio = sum(back_ratios) / len(back_ratios)

            if abs(avg_front_ratio - avg_back_ratio) > 0.1:
                result.warnings.append(
                    f"Разные пропорции изображений: лицевые {avg_front_ratio:.2f}, "
                    f"оборотные {avg_back_ratio:.2f}"
                )

    # Информационные сообщения
    if front_count > 0:
        result.infos.append(f"Лицевых сторон: {front_count}")
    if back_count > 0:
        result.infos.append(f"Оборотных сторон: {back_count}")
    if scheme != '1:1':
        result.infos.append(f"Схема сопоставления: {scheme}")

    return result


def check_safe_zone_compliance(image_info, card_width, card_height, bleed, safe_zone_margin=5):
    """Проверить соответствие безопасной зоне"""
    issues = []

    if 'size' not in image_info or 'error' in image_info:
        return issues

    img_width, img_height = image_info['size']

    # Расчет размеров с учетом вылетов
    total_width = card_width + 2 * bleed
    total_height = card_height + 2 * bleed

    # Расчет безопасной зоны
    safe_zone_width = card_width - 2 * safe_zone_margin
    safe_zone_height = card_height - 2 * safe_zone_margin

    # Проверка масштаба
    scale_x = img_width / total_width
    scale_y = img_height / total_height
    scale = min(scale_x, scale_y)

    # Проверка, помещается ли безопасная зона
    scaled_safe_width = safe_zone_width * scale
    scaled_safe_height = safe_zone_height * scale

    if img_width < scaled_safe_width or img_height < scaled_safe_height:
        issues.append(
            f"Изображение слишком маленькое для безопасной зоны. "
            f"Требуется минимум {math.ceil(scaled_safe_width)}×{math.ceil(scaled_safe_height)} пикселей"
        )

    # Проверка соотношения сторон
    image_ratio = img_width / img_height
    card_ratio = card_width / card_height

    if abs(image_ratio - card_ratio) > 0.1:
        issues.append(
            f"Соотношение сторон {image_ratio:.2f} не соответствует визитке {card_ratio:.2f}. "
            f"Возможна обрезка важных элементов"
        )

    return issues


def generate_validation_report(validation_result: ValidationResult) -> str:
    """Сгенерировать детальный отчет о валидации"""
    report = []

    if validation_result.errors:
        report.append("🚨 ОШИБКИ:")
        report.extend([f"  • {error}" for error in validation_result.errors])
        report.append("")

    if validation_result.warnings:
        report.append("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        report.extend([f"  • {warning}" for warning in validation_result.warnings])
        report.append("")

    if validation_result.dpi_issues:
        report.append("📏 ПРОБЛЕМЫ С РАЗРЕШЕНИЕМ:")
        report.extend([f"  • {issue}" for issue in validation_result.dpi_issues])
        report.append("")

    if validation_result.color_issues:
        report.append("🎨 ПРОБЛЕМЫ С ЦВЕТОМ:")
        report.extend([f"  • {issue}" for issue in validation_result.color_issues])
        report.append("")

    if validation_result.safe_zone_issues:
        report.append("🛡️ ПРОБЛЕМЫ БЕЗОПАСНОЙ ЗОНЫ:")
        report.extend([f"  • {issue}" for issue in validation_result.safe_zone_issues])
        report.append("")

    if validation_result.infos:
        report.append("ℹ️ ИНФОРМАЦИЯ:")
        report.extend([f"  • {info}" for info in validation_result.infos])

    if not any([validation_result.errors, validation_result.warnings,
                validation_result.dpi_issues, validation_result.color_issues,
                validation_result.safe_zone_issues]):
        report.append("✅ Все проверки пройдены успешно!")

    return "\n".join(report)