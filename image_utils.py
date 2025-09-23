import os
from PIL import Image

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')

def list_image_files(folder):
    files = []
    for filename in os.listdir(folder):
        if filename.lower().endswith(SUPPORTED_FORMATS):
            files.append(os.path.join(folder, filename))
    return files

def get_image_info(filepath):
    try:
        with Image.open(filepath) as img:
            return {
                'filename': os.path.basename(filepath),
                'format': img.format,
                'size': img.size,
                'mode': img.mode
            }
    except Exception as e:
        return {
            'filename': os.path.basename(filepath),
            'error': str(e)
        }

def scan_images(folder):
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