import os
from PIL import Image

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp')


def list_image_files(folder):
    """Получить список изображений в папке"""
    if not folder or not os.path.exists(folder):
        return []

    files = []
    for filename in os.listdir(folder):
        if filename.lower().endswith(SUPPORTED_FORMATS):
            files.append(os.path.join(folder, filename))
    return sorted(files)  # Сортируем для предсказуемости


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


def scan_images(folder):
    """Просканировать папку с изображениями"""
    files = list_image_files(folder)
    infos = []
    errors = []

    for f in files:
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

    # Проверяем соответствие по количеству
    if front_count != back_count and back_count > 0:
        warnings.append(f"Несоответствие количества: {front_count} лиц vs {back_count} рубашек")

    # Проверяем размеры изображений
    for i, front in enumerate(front_infos):
        if back_count > i:
            back = back_infos[i]
            if front['size'] != back['size']:
                warnings.append(f"Разный размер: {front['filename']} vs {back['filename']}")

    return errors, warnings