import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import os

from config import PrintConfig, SHEET_SIZES, CARD_SIZES
from image_utils import scan_images, validate_image_pairs
from layout_calculator import LayoutCalculator
from pdf_generator import PDFGenerator


class ImpositionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Визиточный импозер v2.0")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)

        self.config = PrintConfig()
        self.front_images = []
        self.back_images = []

        try:
            img = Image.new('RGB', (1, 1), color='white')
            self.icon = ImageTk.PhotoImage(img)
            self.root.iconphoto(False, self.icon)
        except:
            pass

        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        main_frame = ttk.Frame(notebook, padding=10)
        notebook.add(main_frame, text="Основные настройки")

        preview_frame = ttk.Frame(notebook)
        notebook.add(preview_frame, text="Предпросмотр")

        self.setup_main_tab(main_frame)
        self.setup_preview_tab(preview_frame)

        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def setup_main_tab(self, parent):
        """Настройка основной вкладки"""
        parent.columnconfigure(1, weight=1)

        row = 0

        title = ttk.Label(parent, text="Раскладка визиток для печати",
                          font=("Arial", 16, "bold"))
        title.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1

        folder_frame = ttk.LabelFrame(parent, text="Файлы изображений", padding=10)  # UPDATED: текст
        folder_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        folder_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(folder_frame, text="Лицевые стороны:").grid(row=0, column=0, sticky="w", pady=2)
        self.front_entry = ttk.Entry(folder_frame)
        self.front_entry.grid(row=0, column=1, sticky="we", padx=5)
        self.front_entry.configure(state='readonly')  # NEW: только для чтения
        ttk.Button(folder_frame, text="Обзор", command=self.select_front_files).grid(row=0, column=2)  # UPDATED: select_front_files

        ttk.Label(folder_frame, text="Оборотные стороны:").grid(row=1, column=0, sticky="w", pady=2)
        self.back_entry = ttk.Entry(folder_frame)
        self.back_entry.grid(row=1, column=1, sticky="we", padx=5)
        self.back_entry.configure(state='readonly')  # NEW: только для чтения
        ttk.Button(folder_frame, text="Обзор", command=self.select_back_files).grid(row=1, column=2)  # UPDATED: select_back_files

        print_frame = ttk.LabelFrame(parent, text="Параметры печати", padding=10)
        print_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        print_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(print_frame, text="Размер листа:").grid(row=0, column=0, sticky="w", pady=2)
        self.sheet_combo = ttk.Combobox(print_frame, values=list(SHEET_SIZES.keys()), width=15)
        self.sheet_combo.set(self.config.sheet_size)
        self.sheet_combo.grid(row=0, column=1, sticky="w", pady=2)
        self.sheet_combo.bind('<<ComboboxSelected>>', self.on_config_change)

        ttk.Label(print_frame, text="Размер визитки:").grid(row=1, column=0, sticky="w", pady=2)
        self.card_combo = ttk.Combobox(print_frame, values=list(CARD_SIZES.keys()), width=20)
        self.card_combo.set(self.config.card_size)
        self.card_combo.grid(row=1, column=1, sticky="w", pady=2)
        self.card_combo.bind('<<ComboboxSelected>>', self.on_config_change)

        self.custom_size_frame = ttk.Frame(print_frame)
        self.custom_size_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=2)

        ttk.Label(self.custom_size_frame, text="Ширина:").pack(side=tk.LEFT)
        self.card_width_spin = ttk.Spinbox(self.custom_size_frame, from_=10, to=200, width=5)
        self.card_width_spin.set(self.config.custom_card_width)
        self.card_width_spin.pack(side=tk.LEFT, padx=5)
        self.card_width_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(self.custom_size_frame, text="Высота:").pack(side=tk.LEFT)
        self.card_height_spin = ttk.Spinbox(self.custom_size_frame, from_=10, to=200, width=5)
        self.card_height_spin.set(self.config.custom_card_height)
        self.card_height_spin.pack(side=tk.LEFT, padx=5)
        self.card_height_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(self.custom_size_frame, text="мм").pack(side=tk.LEFT)

        ttk.Label(print_frame, text="Поля:").grid(row=3, column=0, sticky="w", pady=2)
        self.margin_spin = ttk.Spinbox(print_frame, from_=0, to=50, width=5)
        self.margin_spin.set(self.config.margin)
        self.margin_spin.grid(row=3, column=1, sticky="w", pady=2)
        self.margin_spin.bind('<KeyRelease>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=3, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Вылет под обрез:").grid(row=4, column=0, sticky="w", pady=2)
        self.bleed_spin = ttk.Spinbox(print_frame, from_=0, to=10, width=5)
        self.bleed_spin.set(self.config.bleed)
        self.bleed_spin.grid(row=4, column=1, sticky="w", pady=2)
        self.bleed_spin.bind('<KeyRelease>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=4, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Зазор между визитками:").grid(row=5, column=0, sticky="w", pady=2)
        self.gutter_spin = ttk.Spinbox(print_frame, from_=0, to=20, width=5)
        self.gutter_spin.set(self.config.gutter)
        self.gutter_spin.grid(row=5, column=1, sticky="w", pady=2)
        self.gutter_spin.bind('<KeyRelease>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=5, column=2, sticky="w", pady=2)

        options_frame = ttk.Frame(print_frame)
        options_frame.grid(row=6, column=0, columnspan=3, sticky="w", pady=5)

        self.rotate_var = tk.BooleanVar(value=self.config.rotate_cards)
        self.rotate_cb = ttk.Checkbutton(options_frame, text="Поворачивать для экономии места",
                                         variable=self.rotate_var, command=self.on_config_change)
        self.rotate_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.crop_var = tk.BooleanVar(value=self.config.add_crop_marks)
        self.crop_cb = ttk.Checkbutton(options_frame, text="Добавлять обрезные метки",
                                       variable=self.crop_var, command=self.on_config_change)
        self.crop_cb.pack(side=tk.LEFT)

        info_frame = ttk.LabelFrame(parent, text="Информация о раскладке", padding=10)
        info_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        info_frame.columnconfigure(0, weight=1)
        row += 1

        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky="we")

        buttons_frame = ttk.Frame(parent, padding=10)
        buttons_frame.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        ttk.Button(buttons_frame, text="Загрузить изображения", command=self.load_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Сгенерировать PDF", command=self.generate_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Очистить", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def setup_preview_tab(self, parent):
        """Настройка вкладки предпросмотра"""
        self.preview_frame = parent

    def select_front_files(self):  # NEW
        files = filedialog.askopenfilenames(
            title="Выберите файлы лицевых сторон",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"),
                       ("All files", "*.*")]
        )
        if files:
            self.config.front_files = list(files)
            self.front_entry.configure(state='normal')
            self.front_entry.delete(0, tk.END)
            self.front_entry.insert(0, "; ".join(os.path.basename(f) for f in files))
            self.front_entry.configure(state='readonly')
            self.load_images()

    def select_back_files(self):  # NEW
        files = filedialog.askopenfilenames(
            title="Выберите файлы оборотных сторон",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"),
                       ("All files", "*.*")]
        )
        if files:
            self.config.back_files = list(files)
            self.back_entry.configure(state='normal')
            self.back_entry.delete(0, tk.END)
            self.back_entry.insert(0, "; ".join(os.path.basename(f) for f in files))
            self.back_entry.configure(state='readonly')
            self.load_images()

    def on_config_change(self, event=None):
        """Обработчик изменения настроек"""
        self.update_config_from_ui()
        self.update_preview()

    def update_config_from_ui(self):
        """Обновить конфиг из UI"""
        self.config.sheet_size = self.sheet_combo.get()
        self.config.card_size = self.card_combo.get()

        try:
            self.config.custom_card_width = int(self.card_width_spin.get())
            self.config.custom_card_height = int(self.card_height_spin.get())
            self.config.margin = int(self.margin_spin.get())
            self.config.bleed = int(self.bleed_spin.get())
            self.config.gutter = int(self.gutter_spin.get())
        except ValueError:
            pass

        self.config.rotate_cards = self.rotate_var.get()
        self.config.add_crop_marks = self.crop_var.get()

        self.update_custom_size_visibility()

    def update_custom_size_visibility(self):
        """Показать/скрыть поля для произвольного размера"""
        if self.config.card_size == 'Произвольный':
            self.custom_size_frame.grid()
        else:
            self.custom_size_frame.grid_remove()

    def load_images(self):
        """Загрузить изображения из выбранных файлов"""
        self.update_config_from_ui()

        self.front_images = []
        self.back_images = []

        # Загружаем лицевые стороны
        if self.config.front_files:
            front_infos, front_errors = scan_images(self.config.front_files)  # UPDATED: передаем список файлов
            self.front_images = [info['path'] for info in front_infos]

        # Загружаем оборотные стороны
        if self.config.back_files:
            back_infos, back_errors = scan_images(self.config.back_files)  # UPDATED: передаем список файлов
            self.back_images = [info['path'] for info in back_infos]

        # Валидируем пары
        errors, warnings = validate_image_pairs(
            [{'path': p} for p in self.front_images],
            [{'path': p} for p in self.back_images]
        )

        # Обновляем информацию
        self.update_layout_info()
        self.update_preview()

        # Показываем предупреждения
        if warnings:
            messagebox.showwarning("Предупреждения", "\n".join(warnings))
        if errors:
            messagebox.showerror("Ошибки", "\n".join(errors))

        self.status_var.set(f"Загружено: {len(self.front_images)} лиц, {len(self.back_images)} рубашек")

    def update_layout_info(self):
        """Обновить информацию о раскладке"""
        if not hasattr(self, 'info_text'):
            return

        sheet_w, sheet_h = self.config.get_sheet_dimensions()
        card_w, card_h = self.config.get_card_dimensions()

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            self.config.margin, self.config.bleed, self.config.gutter, self.config.rotate_cards
        )

        layout = calculator.calculate_layout()
        sheets_needed = calculator.calculate_sheets_needed(len(self.front_images))

        info = f"""Размер листа: {sheet_w}×{sheet_h} мм
Размер визитки: {card_w}×{card_h} мм
Раскладка: {layout['cards_x']}×{layout['cards_y']} = {layout['cards_total']} визиток/лист
Эффективность: {layout['efficiency']:.1%}
Потребуется листов: {sheets_needed}
Всего визиток: {len(self.front_images)}"""

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

    def update_preview(self):
        """Обновить предпросмотр"""
        self.update_config_from_ui()
        self.update_layout_info()

        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.preview_frame, text="Предпросмотр раскладки",
                  font=("Arial", 12, "bold")).pack(pady=10)

        sheet_w, sheet_h = self.config.get_sheet_dimensions()
        card_w, card_h = self.config.get_card_dimensions()

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            self.config.margin, self.config.bleed, self.config.gutter, self.config.rotate_cards
        )

        layout = calculator.calculate_layout()

        if layout['cards_total'] > 0:
            preview_text = f"""Лист: {sheet_w}×{sheet_h} мм
Визитки: {layout['cards_x']}×{layout['cards_y']} = {layout['cards_total']} шт.
Поворот: {'Да' if layout['rotated'] else 'Нет'}"""

            ttk.Label(self.preview_frame, text=preview_text,
                      font=("Courier", 10)).pack(pady=5)
        else:
            ttk.Label(self.preview_frame, text="Визитки не помещаются на лист!",
                      foreground="red").pack(pady=5)

    def generate_pdf(self):
        """Сгенерировать PDF файл"""
        if not self.front_images:
            messagebox.showerror("Ошибка", "Нет изображений для генерации PDF")
            return

        output_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Сохранить PDF как"
        )

        if not output_file:
            return

        try:
            generator = PDFGenerator(self.config)
            result = generator.generate_pdf(self.front_images, self.back_images, output_file)

            messagebox.showinfo("Успех",
                                f"PDF успешно создан!\n"
                                f"Файл: {output_file}\n"
                                f"Листов: {result['total_sheets']}\n"
                                f"Визиток на листе: {result['cards_per_sheet']}")

            self.status_var.set(f"PDF создан: {os.path.basename(output_file)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PDF: {str(e)}")
            self.status_var.set("Ошибка создания PDF")

    def clear_all(self):
        """Очистить все настройки"""
        self.front_entry.configure(state='normal')
        self.front_entry.delete(0, tk.END)
        self.front_entry.configure(state='readonly')
        self.back_entry.configure(state='normal')
        self.back_entry.delete(0, tk.END)
        self.back_entry.configure(state='readonly')
        self.config = PrintConfig()
        self.front_images = []
        self.back_images = []

        self.sheet_combo.set(self.config.sheet_size)
        self.card_combo.set(self.config.card_size)
        self.card_width_spin.set(self.config.custom_card_width)
        self.card_height_spin.set(self.config.custom_card_height)
        self.margin_spin.set(self.config.margin)
        self.bleed_spin.set(self.config.bleed)
        self.gutter_spin.set(self.config.gutter)
        self.rotate_var.set(self.config.rotate_cards)
        self.crop_var.set(self.config.add_crop_marks)

        self.update_custom_size_visibility()
        self.update_preview()
        self.status_var.set("Все настройки очищены")


def main():
    root = tk.Tk()
    app = ImpositionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()