from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PIL import Image
import os

def make_layout_pdf(image_paths, out_path, card_w_mm=90, card_h_mm=50,
                    sheet_w_mm=210, sheet_h_mm=297, cards_x=2, cards_y=5, margin_mm=5):
    c = canvas.Canvas(out_path, pagesize=(sheet_w_mm * mm, sheet_h_mm * mm))
    card_w, card_h = card_w_mm * mm, card_h_mm * mm
    margin = margin_mm * mm

    i = 0
    temp_files = []
    for y in range(cards_y):
        for x in range(cards_x):
            if i >= len(image_paths):
                break
            x_pos = margin + x * card_w
            y_pos = margin + y * card_h
            try:
                print(f"Opening {image_paths[i]}")
                img = Image.open(image_paths[i])
                print(f"Type after open: {type(img)}")
                img_rgb = img.convert('RGB')
                print(f"Type after convert: {type(img_rgb)}")
                temp_img_path = f"_temp_img_{i}.png"
                img_rgb.save(temp_img_path, format='PNG')
                temp_files.append(temp_img_path)
                c.drawImage(ImageReader(temp_img_path), x_pos, sheet_h_mm * mm - y_pos - card_h, card_w, card_h)
            except Exception as e:
                print(f"Error processing {image_paths[i]}: {e}")
            i += 1

    c.save()

    for temp_img_path in temp_files:
        try:
            os.remove(temp_img_path)
        except Exception:
            pass