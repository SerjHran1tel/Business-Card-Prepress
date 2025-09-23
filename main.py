from image_utils import scan_images
from layout import make_layout_pdf

def main():
    folder = "Pictures"
    print(f"Scanning folder: {folder}")
    infos, errors = scan_images(folder)

    print("\nImages found:")
    image_files = []
    for info in infos:
        print(f"{info['filename']}: {info['format']}, size={info['size']}, mode={info['mode']}")
        image_files.append(f"{folder}/{info['filename']}")

    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"{err['filename']}: {err['error']}")
    else:
        print("\nNo errors found.")

    if image_files:
        # Генерируем PDF-раскладку по первым N изображениям
        print("\nGenerating layout PDF...")
        out_pdf = "business_cards_layout.pdf"
        make_layout_pdf(image_files[:10], out_pdf)
        print(f"PDF saved as {out_pdf}")
    else:
        print("No images for layout.")

if __name__ == "__main__":
    main()