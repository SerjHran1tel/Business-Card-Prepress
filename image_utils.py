from PIL import Image
import os

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp')  # Пока только растр; PDF/EPS требуют доп. libs

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

def validate_image_pairs(front_infos, back_infos, scheme='1:1', match_by_name=False):
    """Проверить соответствие лицевых и оборотных сторон"""
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