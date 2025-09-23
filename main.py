import os
from image_utils import scan_images

def main():
    print("Business Card Prepress: этап 2 — обработка изображений.")
    pictures_folder = 'Pictures'
    if not os.path.exists(pictures_folder):
        print(f"Папка '{pictures_folder}' не найдена.")
        return

    infos, errors = scan_images(pictures_folder)
    print("\nНайденные изображения:")
    for info in infos:
        print(f"  {info['filename']}: {info['format']}, размер {info['size']}, режим {info['mode']}")
    if errors:
        print("\nОшибки при обработке файлов:")
        for err in errors:
            print(f"  {err['filename']}: {err['error']}")
    else:
        print("\nОшибочных файлов не обнаружено.")

if __name__ == "__main__":
    main()