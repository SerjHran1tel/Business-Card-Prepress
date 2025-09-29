from PIL import Image
import os

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp')

def get_image_info(filepath):
    """Получить информацию об изображении"""
    try:
        with Image.open(filepath) as img:
            return {
                'filename': os.path.basename(filepath),
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'path': filepath
            }
    except Exception as e:
        return {
            'filename': os.path.basename(filepath),
            'error': str(e),
            'path': filepath
        }

def scan_images(file_list):
    """Просканировать список файлов изображений"""
    if not file_list:
        return [], []

    infos = []
    errors = []

    for f in file_list:
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

def validate_image_pairs(front_infos, back_infos):
    """Проверить соответствие лицевых и оборотных сторон"""
    errors = []
    warnings = []

    front_count = len(front_infos)
    back_count = len(back_infos)

    if front_count == 0:
        errors.append("Не найдено лицевых сторон")
    if back_count == 0:
        warnings.append("Не найдено оборотных сторон (будет создана односторонняя раскладка)")

    if front_count != back_count and back_count > 0:
        warnings.append(f"Несоответствие количества: {front_count} лиц vs {back_count} рубашек")

    for i, front in enumerate(front_infos):
        if back_count > i:
            back = back_infos[i]
            if front['size'] != back['size']:
                warnings.append(f"Разный размер: {front['filename']} vs {back['filename']}")

    return errors, warnings