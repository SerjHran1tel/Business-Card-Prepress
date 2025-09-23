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

        # Создаем иконку (если есть PIL)
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
        # Создаем панель вкладок
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка основных настроек
        main_frame = ttk.Frame(notebook, padding=10)
        notebook.add(main_frame, text="Основные настройки")

        # Вкладка предпросмотра
        preview_frame = ttk.Frame(notebook)
        notebook.add(preview_frame, text="Предпросмотр")

        self.setup_main_tab(main_frame)
        self.setup_preview_tab(preview_frame)

        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def setup_main_tab(self, parent):
        """Настройка основной вкладки"""
        # Сетка для выравнивания
        parent.columnconfigure(1, weight=1)

        row = 0

        # Заголовок
        title = ttk.Label(parent, text="Раскладка визиток для печати",
                          font=("Arial", 16, "bold"))
        title.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1

        # Папки с изображениями
        folder_frame = ttk.LabelFrame(parent, text="Папки с изображениями", padding=10)
        folder_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        folder_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(folder_frame, text="Лицевые стороны:").grid(row=0, column=0, sticky="w", pady=2)
        self.front_entry = ttk.Entry(folder_frame, textvariable=tk.StringVar(value=self.config.front_folder))
        self.front_entry.grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(folder_frame, text="Обзор", command=self.select_front_folder).grid(row=0, column=2)

        ttk.Label(folder_frame, text="Оборотные стороны:").grid(row=1, column=0, sticky="w", pady=2)
        self.back_entry = ttk.Entry(folder_frame, textvariable=tk.StringVar(value=self.config.back_folder))
        self.back_entry.grid(row=1, column=1, sticky="we", padx=5)
        ttk.Button(folder_frame, text="Обзор", command=self.select_back_folder).grid(row=1, column=2)

        # Параметры печати
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

        # Произвольный размер визитки
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

        # Дополнительные параметры
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

        # Опции
        options_frame = ttk.Frame(print_frame)
        options_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)

        self.rotate_var = tk.BooleanVar(value=self.config.rotate_cards)
        self.rotate_cb = ttk.Checkbutton(options_frame, text="Поворачивать для экономии места",
                                         variable=self.rotate_var, command=self.on_config_change)
        self.rotate_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.crop_var = tk.BooleanVar(value=self.config.add_crop_marks)
        self.crop_cb = ttk.Checkbutton(options_frame, text="Добавлять обрезные метки",
                                       variable=self.crop_var, command=self.on_config_change)
        self.crop_cb.pack(side=tk.LEFT)

        # Информация о раскладке
        info_frame = ttk.LabelFrame(parent, text="Информация о раскладке", padding=10)
        info_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        info_frame.columnconfigure(0, weight=1)
        row += 1

        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, font=("Courier", 9))
        self.info_text.grid(row=0, column=0, sticky="we")

        # Кнопки управления
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="Загрузить изображения",
                   command=self.load_images).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Предпросмотр",
                   command=self.update_preview).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Сгенерировать PDF",
                   command=self.generate_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить",
                   command=self.clear_all).pack(side=tk.LEFT, padx=5)

        self.update_custom_size_visibility()

    def setup_preview_tab(self, parent):
        """Настройка вкладки предпросмотра"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # Холст для предпросмотра
        self.canvas = tk.Canvas(parent, bg='white', relief='sunken', bd=1)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Полоса прокрутки
        v_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=v_scroll.set)

        h_scroll = ttk.Scrollbar(parent, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=h_scroll.set)

        # Фрейм внутри холста для содержимого
        self.preview_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.preview_frame, anchor="nw")

        self.preview_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))

    def select_front_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с лицевыми сторонами")
        if folder:
            self.front_entry.delete(0, tk.END)
            self.front_entry.insert(0, folder)
            self.config.front_folder = folder
            self.load_images()

    def select_back_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с оборотными сторонами")
        if folder:
            self.back_entry.delete(0, tk.END)
            self.back_entry.insert(0, folder)
            self.config.back_folder = folder
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
        """Загрузить изображения из выбранных папок"""
        self.update_config_from_ui()

        self.front_images = []
        self.back_images = []

        # Загружаем лицевые стороны
        if self.config.front_folder and os.path.exists(self.config.front_folder):
            front_infos, front_errors = scan_images(self.config.front_folder)
            self.front_images = [info['path'] for info in front_infos]

        # Загружаем оборотные стороны
        if self.config.back_folder and os.path.exists(self.config.back_folder):
            back_infos, back_errors = scan_images(self.config.back_folder)
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
            self.config.margin, self.config.bleed, self.config.rotate_cards
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

        # Здесь будет код для визуализации предпросмотра
        # Пока просто очищаем холст
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.preview_frame, text="Предпросмотр раскладки",
                  font=("Arial", 12, "bold")).pack(pady=10)

        # Простая текстовая визуализация
        sheet_w, sheet_h = self.config.get_sheet_dimensions()
        card_w, card_h = self.config.get_card_dimensions()

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            self.config.margin, self.config.bleed, self.config.rotate_cards
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
        self.front_entry.delete(0, tk.END)
        self.back_entry.delete(0, tk.END)
        self.config = PrintConfig()
        self.front_images = []
        self.back_images = []

        # Сброс UI к значениям по умолчанию
        self.sheet_combo.set(self.config.sheet_size)
        self.card_combo.set(self.config.card_size)
        self.card_width_spin.set(self.config.custom_card_width)
        self.card_height_spin.set(self.config.custom_card_height)
        self.margin_spin.set(self.config.margin)
        self.bleed_spin.set(self.config.bleed)
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