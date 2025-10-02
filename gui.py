import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import os
import tempfile
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import FancyBboxPatch

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
        self.parties = []  # NEW: List of {'front': [], 'back': [], 'quantity': int}
        self.current_quantity = 1  # NEW: For current party

        try:
            img = Image.new('RGB', (1, 1), color='white')
            self.icon = ImageTk.PhotoImage(img)
            self.root.iconphoto(False, self.icon)
        except:
            pass

        self.setup_ui()
        self.root.bind('<Configure>', self.on_resize)
        self.preview_width = 800
        self.preview_height = 500
        self.canvas = None

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

        folder_frame = ttk.LabelFrame(parent, text="Файлы изображений", padding=10)
        folder_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        folder_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(folder_frame, text="Лицевые стороны (multiple OK):").grid(row=0, column=0, sticky="w", pady=2)
        self.front_entry = ttk.Entry(folder_frame)
        self.front_entry.grid(row=0, column=1, sticky="we", padx=5)
        self.front_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_front_files).grid(row=0, column=2)

        ttk.Label(folder_frame, text="Оборотные стороны (multiple OK):").grid(row=1, column=0, sticky="w", pady=2)
        self.back_entry = ttk.Entry(folder_frame)
        self.back_entry.grid(row=1, column=1, sticky="we", padx=5)
        self.back_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_back_files).grid(row=1, column=2)

        # NEW: Quantity spinbox
        ttk.Label(folder_frame, text="Количество копий:").grid(row=2, column=0, sticky="w", pady=2)
        self.quantity_spin = ttk.Spinbox(folder_frame, from_=1, to=10000, width=10)
        self.quantity_spin.set(self.current_quantity)
        self.quantity_spin.grid(row=2, column=1, sticky="w", pady=2)
        self.quantity_spin.bind('<KeyRelease>', self.on_quantity_change)

        ttk.Button(folder_frame, text="Загрузить демо", command=self.load_demo).grid(row=3, column=0, columnspan=3, pady=5)

        # NEW: Party buttons
        party_frame = ttk.Frame(folder_frame)
        party_frame.grid(row=4, column=0, columnspan=3, pady=5)
        ttk.Button(party_frame, text="Добавить партию", command=self.add_current_party).pack(side=tk.LEFT, padx=5)
        ttk.Button(party_frame, text="Очистить текущую партию", command=self.clear_current_party).pack(side=tk.LEFT, padx=5)

        print_frame = ttk.LabelFrame(parent, text="Параметры печати", padding=10)
        print_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        print_frame.columnconfigure(1, weight=1)
        row += 1

        ttk.Label(print_frame, text="Размер листа:").grid(row=0, column=0, sticky="w", pady=2)
        self.sheet_combo = ttk.Combobox(print_frame, values=list(SHEET_SIZES.keys()), width=15)
        self.sheet_combo.set(self.config.sheet_size)
        self.sheet_combo.grid(row=0, column=1, sticky="w", pady=2)
        self.sheet_combo.bind('<<ComboboxSelected>>', self.on_config_change)

        self.custom_sheet_frame = ttk.Frame(print_frame)
        self.custom_sheet_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(self.custom_sheet_frame, text="Ширина:").pack(side=tk.LEFT)
        self.sheet_width_spin = ttk.Spinbox(self.custom_sheet_frame, from_=100, to=1000, width=5)
        self.sheet_width_spin.set(self.config.custom_sheet_width)
        self.sheet_width_spin.pack(side=tk.LEFT, padx=5)
        self.sheet_width_spin.bind('<KeyRelease>', self.on_config_change)
        self.sheet_width_spin.bind('<Return>', self.on_config_change)
        ttk.Label(self.custom_sheet_frame, text="Высота:").pack(side=tk.LEFT)
        self.sheet_height_spin = ttk.Spinbox(self.custom_sheet_frame, from_=100, to=1000, width=5)
        self.sheet_height_spin.set(self.config.custom_sheet_height)
        self.sheet_height_spin.pack(side=tk.LEFT, padx=5)
        self.sheet_height_spin.bind('<KeyRelease>', self.on_config_change)
        self.sheet_height_spin.bind('<Return>', self.on_config_change)
        ttk.Label(self.custom_sheet_frame, text="мм").pack(side=tk.LEFT)

        ttk.Label(print_frame, text="Размер визитки:").grid(row=2, column=0, sticky="w", pady=2)
        self.card_combo = ttk.Combobox(print_frame, values=list(CARD_SIZES.keys()), width=20)
        self.card_combo.set(self.config.card_size)
        self.card_combo.grid(row=2, column=1, sticky="w", pady=2)
        self.card_combo.bind('<<ComboboxSelected>>', self.on_config_change)

        self.custom_size_frame = ttk.Frame(print_frame)
        self.custom_size_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=2)

        ttk.Label(self.custom_size_frame, text="Ширина:").pack(side=tk.LEFT)
        self.card_width_spin = ttk.Spinbox(self.custom_size_frame, from_=10, to=200, width=5)
        self.card_width_spin.set(self.config.custom_card_width)
        self.card_width_spin.pack(side=tk.LEFT, padx=5)
        self.card_width_spin.bind('<KeyRelease>', self.on_config_change)
        self.card_width_spin.bind('<Return>', self.on_config_change)

        ttk.Label(self.custom_size_frame, text="Высота:").pack(side=tk.LEFT)
        self.card_height_spin = ttk.Spinbox(self.custom_size_frame, from_=10, to=200, width=5)
        self.card_height_spin.set(self.config.custom_card_height)
        self.card_height_spin.pack(side=tk.LEFT, padx=5)
        self.card_height_spin.bind('<KeyRelease>', self.on_config_change)
        self.card_height_spin.bind('<Return>', self.on_config_change)

        ttk.Label(self.custom_size_frame, text="мм").pack(side=tk.LEFT)

        ttk.Label(print_frame, text="Поля:").grid(row=4, column=0, sticky="w", pady=2)
        self.margin_spin = ttk.Spinbox(print_frame, from_=0, to=50, width=5)
        self.margin_spin.set(self.config.margin)
        self.margin_spin.grid(row=4, column=1, sticky="w", pady=2)
        self.margin_spin.bind('<KeyRelease>', self.on_config_change)
        self.margin_spin.bind('<Return>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=4, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Вылет под обрез:").grid(row=5, column=0, sticky="w", pady=2)
        self.bleed_spin = ttk.Spinbox(print_frame, from_=0, to=10, width=5)
        self.bleed_spin.set(self.config.bleed)
        self.bleed_spin.grid(row=5, column=1, sticky="w", pady=2)
        self.bleed_spin.bind('<KeyRelease>', self.on_config_change)
        self.bleed_spin.bind('<Return>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=5, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Зазор между визитками:").grid(row=6, column=0, sticky="w", pady=2)
        self.gutter_spin = ttk.Spinbox(print_frame, from_=0, to=20, width=5)
        self.gutter_spin.set(self.config.gutter)
        self.gutter_spin.grid(row=6, column=1, sticky="w", pady=2)
        self.gutter_spin.bind('<KeyRelease>', self.on_config_change)
        self.gutter_spin.bind('<Return>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=6, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Длина обрезных меток:").grid(row=7, column=0, sticky="w", pady=2)
        self.mark_length_spin = ttk.Spinbox(print_frame, from_=1, to=20, width=5)
        self.mark_length_spin.set(self.config.mark_length)
        self.mark_length_spin.grid(row=7, column=1, sticky="w", pady=2)
        self.mark_length_spin.bind('<KeyRelease>', self.on_config_change)
        self.mark_length_spin.bind('<Return>', self.on_config_change)
        ttk.Label(print_frame, text="мм").grid(row=7, column=2, sticky="w", pady=2)

        ttk.Label(print_frame, text="Схема сопоставления:").grid(row=8, column=0, sticky="w", pady=2)
        self.scheme_combo = ttk.Combobox(print_frame, values=['1:1', '1:N', 'M:N'], width=10)
        self.scheme_combo.set(self.config.matching_scheme)
        self.scheme_combo.grid(row=8, column=1, sticky="w", pady=2)
        self.scheme_combo.bind('<<ComboboxSelected>>', self.on_config_change)

        options_frame = ttk.Frame(print_frame)
        options_frame.grid(row=9, column=0, columnspan=3, sticky="w", pady=5)

        self.rotate_var = tk.BooleanVar(value=self.config.rotate_cards)
        self.rotate_cb = ttk.Checkbutton(options_frame, text="Поворачивать для экономии места",
                                         variable=self.rotate_var, command=self.on_config_change)
        self.rotate_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.crop_var = tk.BooleanVar(value=self.config.add_crop_marks)
        self.crop_cb = ttk.Checkbutton(options_frame, text="Добавлять обрезные метки",
                                       variable=self.crop_var, command=self.on_config_change)
        self.crop_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.fit_var = tk.BooleanVar(value=self.config.fit_proportions)
        self.fit_cb = ttk.Checkbutton(options_frame, text="Подгонка пропорций (fit)",
                                      variable=self.fit_var, command=self.on_config_change)
        self.fit_cb.pack(side=tk.LEFT, padx=(0, 10))

        self.match_var = tk.BooleanVar(value=self.config.match_by_name)
        self.match_cb = ttk.Checkbutton(options_frame, text="Совпадение по именам",
                                        variable=self.match_var, command=self.on_config_change)
        self.match_cb.pack(side=tk.LEFT)

        info_frame = ttk.LabelFrame(parent, text="Информация о раскладке", padding=10)
        info_frame.grid(row=row, column=0, columnspan=3, sticky="we", pady=5)
        info_frame.columnconfigure(0, weight=1)
        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky="we", pady=5)

        # NEW: Parties list (simple text display)
        self.parties_text = tk.Text(parent, height=4, width=80, wrap=tk.WORD)
        self.parties_text.grid(row=row+1, column=0, columnspan=3, sticky="we", pady=5)

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row+2, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Завершить и сгенерировать PDF", command=self.generate_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить все партии", command=self.clear_all_parties).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def setup_preview_tab(self, parent):
        """Настройка вкладки предпросмотра"""
        ttk.Label(parent, text="Визуальный предпросмотр раскладки", font=("Arial", 12, "bold")).pack(pady=10)
        self.preview_container = ttk.Frame(parent)
        self.preview_container.pack(fill=tk.BOTH, expand=True, pady=10)

    def on_resize(self, event):
        """Обработчик изменения размера окна"""
        if event.widget == self.root and hasattr(self, 'preview_container'):
            new_width = self.preview_container.winfo_width()
            new_height = self.preview_container.winfo_height()
            if new_width > 0 and new_height > 0 and (new_width != self.preview_width or new_height != self.preview_height):
                self.preview_width = new_width
                self.preview_height = new_height
                self.update_preview()

    def on_quantity_change(self, event=None):
        """Обработчик изменения количества"""
        try:
            self.current_quantity = int(self.quantity_spin.get())
        except ValueError:
            pass
        self.update_preview()

    def add_current_party(self):
        """Добавить текущую партию к списку"""
        if not self.front_images:
            messagebox.showerror("Ошибка", "Выберите файлы для партии!")
            return

        party = {
            'front': self.front_images[:],  # Copy lists
            'back': self.back_images[:],
            'quantity': self.current_quantity
        }
        self.parties.append(party)

        # Clear current for next
        self.clear_current_party()

        self.update_parties_display()
        self.update_preview()
        messagebox.showinfo("Успех", f"Добавлена партия: {len(party['front'])} дизайнов × {party['quantity']} копий")

    def clear_current_party(self):
        """Очистить текущую партию (для следующей)"""
        self.front_images = []
        self.back_images = []
        self.current_quantity = 1
        self.quantity_spin.set(1)
        self.front_entry.configure(state='normal')
        self.front_entry.delete(0, tk.END)
        self.front_entry.configure(state='readonly')
        self.back_entry.configure(state='normal')
        self.back_entry.delete(0, tk.END)
        self.back_entry.configure(state='readonly')
        self.update_preview()

    def clear_all_parties(self):
        """Очистить все партии"""
        self.parties = []
        self.clear_current_party()
        self.update_parties_display()
        self.update_preview()
        messagebox.showinfo("Очищено", "Все партии удалены")

    def update_parties_display(self):
        """Обновить отображение списка партий"""
        text = "Партии:\n"
        total_cards = 0
        for i, party in enumerate(self.parties, 1):
            num_designs = len(party['front'])
            text += f"Партия {i}: {num_designs} дизайнов × {party['quantity']} копий = {num_designs * party['quantity']} визиток\n"
            total_cards += num_designs * party['quantity']
        text += f"\nОбщее количество визиток: {total_cards}"
        self.parties_text.delete(1.0, tk.END)
        self.parties_text.insert(1.0, text)

    def load_demo(self):
        """Загрузить демо-изображения"""
        try:
            self.config.front_files = []
            self.config.back_files = []

            front_temp_files = []
            back_temp_files = []
            for i in range(5):
                temp_front = tempfile.NamedTemporaryFile(suffix=f'_front_{i+1}.png', delete=False)
                img_front = Image.new('RGB', (90, 50), color=(i*50, 100, 200))
                img_front.save(temp_front.name)
                temp_front.close()
                front_temp_files.append(temp_front.name)
                self.config.front_files.append(temp_front.name)

                temp_back = tempfile.NamedTemporaryFile(suffix=f'_back_{i+1}.png', delete=False)
                img_back = Image.new('RGB', (90, 50), color=(200, 100, i*50))
                img_back.save(temp_back.name)
                temp_back.close()
                back_temp_files.append(temp_back.name)
                self.config.back_files.append(temp_back.name)

            self.front_entry.delete(0, tk.END)
            self.front_entry.insert(0, os.path.basename(front_temp_files[0]))
            self.back_entry.delete(0, tk.END)
            self.back_entry.insert(0, os.path.basename(back_temp_files[0]))

            # Load to current
            self.load_images_current()
        except Exception as e:
            messagebox.showerror("Ошибка демо", f"Не удалось создать демо: {e}")

    def select_front_files(self):
        """Выбор файлов лицевых сторон"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы лицевых сторон",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"), ("Все файлы", "*.*")]
        )
        if files:
            self.config.front_files = list(files)
            first_name = os.path.basename(files[0])
            display_text = first_name if len(files) == 1 else f"{first_name} (и {len(files)-1} других)"
            self.front_entry.delete(0, tk.END)
            self.front_entry.insert(0, display_text)
            self.front_entry.configure(state='readonly')
            self.load_images_current()

    def select_back_files(self):
        """Выбор файлов оборотных сторон"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы оборотных сторон",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"), ("Все файлы", "*.*")]
        )
        if files:
            self.config.back_files = list(files)
            first_name = os.path.basename(files[0])
            display_text = first_name if len(files) == 1 else f"{first_name} (и {len(files)-1} других)"
            self.back_entry.delete(0, tk.END)
            self.back_entry.insert(0, display_text)
            self.back_entry.configure(state='readonly')
            self.load_images_current()

    def load_images_current(self):  # UPDATED: For current party
        """Загрузить изображения для текущей партии"""
        self.update_config_from_ui()

        self.front_images = []
        self.back_images = []

        if self.config.front_files:
            front_infos, front_errors = scan_images(self.config.front_files, scan_folder=False)
            self.front_images = [info['path'] for info in front_infos]

        if self.config.back_files:
            back_infos, back_errors = scan_images(self.config.back_files, scan_folder=False)
            self.back_images = [info['path'] for info in back_infos]

        front_info_list = []
        for p in self.front_images:
            try:
                front_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': Image.open(p).size})
            except:
                pass
        back_info_list = []
        for p in self.back_images:
            try:
                back_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': Image.open(p).size})
            except:
                pass

        errors, warnings = validate_image_pairs(
            front_info_list, back_info_list, self.config.matching_scheme, self.config.match_by_name
        )

        if errors:
            messagebox.showerror("Ошибки", "\n".join(errors))
        if warnings:
            messagebox.showwarning("Предупреждения", "\n".join(warnings))

        self.status_var.set(f"Текущая партия: {len(self.front_images)} лиц, {len(self.back_images)} рубашек")
        self.update_preview()

    def on_config_change(self, event=None):
        """Обработчик изменения настроек"""
        self.update_config_from_ui()
        self.update_preview()

    def update_config_from_ui(self):
        """Обновить конфиг из UI"""
        self.config.sheet_size = self.sheet_combo.get()
        self.config.custom_sheet = (self.config.sheet_size == 'Произвольный')
        if self.config.custom_sheet:
            try:
                self.config.custom_sheet_width = int(self.sheet_width_spin.get())
                self.config.custom_sheet_height = int(self.sheet_height_spin.get())
            except ValueError:
                pass

        self.config.card_size = self.card_combo.get()

        try:
            self.config.custom_card_width = int(self.card_width_spin.get())
            self.config.custom_card_height = int(self.card_height_spin.get())
            self.config.margin = int(self.margin_spin.get())
            self.config.bleed = int(self.bleed_spin.get())
            self.config.gutter = int(self.gutter_spin.get())
            self.config.mark_length = int(self.mark_length_spin.get())
        except ValueError:
            pass

        self.config.matching_scheme = self.scheme_combo.get()

        self.config.rotate_cards = self.rotate_var.get()
        self.config.add_crop_marks = self.crop_var.get()
        self.config.fit_proportions = self.fit_var.get()
        self.config.match_by_name = self.match_var.get()

        self.update_custom_size_visibility()
        self.update_custom_sheet_visibility()

    def update_custom_sheet_visibility(self):
        """Показать/скрыть поля для произвольного размера листа"""
        if self.config.custom_sheet:
            self.custom_sheet_frame.grid()
        else:
            self.custom_sheet_frame.grid_remove()

    def update_custom_size_visibility(self):
        """Показать/скрыть поля для произвольного размера"""
        if self.config.card_size == 'Произвольный':
            self.custom_size_frame.grid()
        else:
            self.custom_size_frame.grid_remove()

    def get_total_cards(self):
        """Получить общее количество визиток из всех партий"""
        return sum(len(party['front']) * party['quantity'] for party in self.parties)

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
        total_cards = self.get_total_cards()
        sheets_needed = calculator.calculate_sheets_needed(total_cards) if total_cards > 0 else 0

        info = f"""Размер листа: {sheet_w}×{sheet_h} мм
Размер визитки: {card_w}×{card_h} мм
Раскладка: {layout['cards_x']}×{layout['cards_y']} = {layout['cards_total']} визиток/лист
Эффективность: {layout['efficiency']:.1%}
Потребуется листов: {sheets_needed}
Всего визиток: {total_cards}
Схема: {self.config.matching_scheme}
Партий: {len(self.parties)}"""

        if total_cards == 0:
            info += "\n\nДобавьте хотя бы одну партию для полного расчета!"

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)

    def update_preview(self):
        """Обновить предпросмотр"""
        self.update_config_from_ui()
        self.update_layout_info()

        for widget in self.preview_container.winfo_children():
            widget.destroy()

        total_cards = self.get_total_cards()
        if total_cards == 0 and len(self.front_images) == 0:
            ttk.Label(self.preview_container, text="Выберите файлы и добавьте партию для предпросмотра\n(или нажмите 'Загрузить демо')",
                      font=("Arial", 10), foreground="orange").pack(pady=20)
            return

        sheet_w, sheet_h = self.config.get_sheet_dimensions()
        card_w, card_h = self.config.get_card_dimensions()

        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            self.config.margin, self.config.bleed, self.config.gutter, self.config.rotate_cards
        )

        layout = calculator.calculate_layout()

        if layout['cards_total'] == 0:
            ttk.Label(self.preview_container, text="Визитки не помещаются на лист!", foreground="red").pack(pady=5)
            return

        fig_width = max(8, self.preview_width / 100)
        fig_height = max(6, self.preview_height / 100)
        fig = Figure(figsize=(fig_width, fig_height), dpi=100)
        fig.suptitle("Предпросмотр раскладки (левый: передняя, правый: задняя)", fontsize=12)

        ax_front = fig.add_subplot(121)
        ax_front.set_xlim(0, sheet_w)
        ax_front.set_ylim(0, sheet_h)
        ax_front.set_aspect('equal')
        ax_front.invert_yaxis()
        ax_front.set_title("Передняя сторона")

        ax_back = fig.add_subplot(122)
        ax_back.set_xlim(0, sheet_w)
        ax_back.set_ylim(0, sheet_h)
        ax_back.set_aspect('equal')
        ax_back.invert_yaxis()

        if len(self.back_images) > 0:
            ax_back.set_title("Задняя сторона")
            if self.config.matching_scheme != '1:1':
                if self.config.matching_scheme == '1:N':
                    self.back_images_preview = [self.back_images[0]] * len(self.front_images)
                elif self.config.matching_scheme == 'M:N':
                    self.back_images_preview = [self.back_images[i % len(self.back_images)] for i in range(len(self.front_images))]
            else:
                self.back_images_preview = self.back_images
        else:
            ax_back.set_title("Задняя сторона (отсутствует)")
            ax_back.text(0.5, 0.5, "Нет оборотных сторон\n(односторонняя печать)", ha='center', va='center', transform=ax_back.transAxes, fontsize=10, color='orange')

        # Draw styled margins for both axes
        for ax in [ax_front, ax_back]:
            sheet_rect = FancyBboxPatch((0, 0), sheet_w, sheet_h, boxstyle="round,pad=0.01",
                                        edgecolor='gray', facecolor='lightgray', alpha=0.1, linewidth=2)
            ax.add_patch(sheet_rect)
            ax.text(sheet_w/2, -sheet_h*0.05, 'Sheet (Margins)', ha='center', fontsize=8, color='gray', transform=ax.transData)

            work_x = self.config.margin
            work_y = self.config.margin
            work_w = sheet_w - 2 * self.config.margin
            work_h = sheet_h - 2 * self.config.margin
            work_rect = FancyBboxPatch((work_x, work_y), work_w, work_h, boxstyle="round,pad=0.005",
                                       edgecolor='blue', facecolor='lightblue', alpha=0.2, linewidth=1.5)
            ax.add_patch(work_rect)
            ax.text(work_x + work_w/2, work_y - 5, 'Work Area', ha='center', fontsize=8, color='blue', transform=ax.transData)

        # Function to draw side (use current images for preview)
        def draw_side(ax, images_list):
            for i, pos in enumerate(layout['positions']):
                if i >= len(images_list):
                    break
                inner_x = pos['x'] + self.config.bleed
                inner_y = pos['y'] + self.config.bleed

                bleed_rect = FancyBboxPatch((pos['x'], pos['y']), pos['width'], pos['height'],
                                             boxstyle="round,pad=0.005", edgecolor='green', facecolor='lightgreen',
                                             alpha=0.15, linewidth=1)
                ax.add_patch(bleed_rect)
                ax.text(pos['x'] + pos['width']/2, pos['y'] - 2, 'Bleed', ha='center', fontsize=7, color='green', transform=ax.transData)

                inner_rect = FancyBboxPatch((inner_x, inner_y), card_w, card_h, boxstyle="round,pad=0.005",
                                            edgecolor='black', facecolor='white', linewidth=1.5)
                ax.add_patch(inner_rect)
                ax.text(inner_x + card_w/2, inner_y + card_h + 2, 'Card', ha='center', fontsize=7, color='black', transform=ax.transData)

                if i < len(images_list):
                    try:
                        img_path = images_list[i]
                        img = Image.open(img_path)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        preview_scale = 2
                        img_resized = img.resize((int(card_w * preview_scale), int(card_h * preview_scale)), Image.Resampling.LANCZOS)
                        arr = np.array(img_resized)
                        im = OffsetImage(arr, zoom=1.0 / preview_scale)
                        ab = AnnotationBbox(im, (inner_x + card_w / 2, inner_y + card_h / 2),
                                            xybox=(0, 0), frameon=False, pad=0, boxcoords="offset points")
                        ax.add_artist(ab)
                    except Exception as e:
                        print(f"Ошибка загрузки изображения {img_path} для preview: {e}")

                if self.config.add_crop_marks:
                    mark_len = self.config.mark_length
                    ax.plot([inner_x, inner_x], [inner_y, inner_y + mark_len], 'k-', lw=0.5)
                    ax.plot([inner_x, inner_x - mark_len], [inner_y, inner_y], 'k-', lw=0.5)
                    ax.plot([inner_x + card_w, inner_x + card_w], [inner_y, inner_y + mark_len], 'k-', lw=0.5)
                    ax.plot([inner_x + card_w, inner_x + card_w + mark_len], [inner_y, inner_y], 'k-', lw=0.5)
                    ax.plot([inner_x, inner_x], [inner_y + card_h, inner_y + card_h - mark_len], 'k-', lw=0.5)
                    ax.plot([inner_x, inner_x - mark_len], [inner_y + card_h, inner_y + card_h], 'k-', lw=0.5)
                    ax.plot([inner_x + card_w, inner_x + card_w], [inner_y + card_h, inner_y + card_h - mark_len], 'k-', lw=0.5)
                    ax.plot([inner_x + card_w, inner_x + card_w + mark_len], [inner_y + card_h, inner_y + card_h], 'k-', lw=0.5)

        # Draw current front/back for preview
        draw_side(ax_front, self.front_images)

        if len(self.back_images) > 0:
            draw_side(ax_back, self.back_images_preview if hasattr(self, 'back_images_preview') else self.back_images)
        else:
            messagebox.showwarning("Предупреждение", "Не найдено оборотных сторон (будет создана односторонняя раскладка)")

        for ax in [ax_front, ax_back]:
            ax.axis('off')

        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(fig, master=self.preview_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        preview_text = f"""Лист: {sheet_w}×{sheet_h} мм
Визитки: {layout['cards_x']}×{layout['cards_y']} = {layout['cards_total']} шт.
Поворот: {'Да' if layout['rotated'] else 'Нет'}"""
        ttk.Label(self.preview_container, text=preview_text, font=("Courier", 10)).pack(pady=5)

    def generate_pdf(self):
        """Сгенерировать PDF файл"""
        total_cards = self.get_total_cards()
        if total_cards == 0:
            messagebox.showerror("Ошибка", "Нет визиток в партиях для генерации PDF. Добавьте партии!")
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
            # NEW: Generate for all parties
            all_front = []
            all_back = []
            for party in self.parties:
                # Repeat files quantity times
                for _ in range(party['quantity']):
                    all_front.extend(party['front'])
                    if party['back']:
                        all_back.extend(party['back'])
                    else:
                        all_back.extend([None] * len(party['front']))  # Placeholder for single-sided

            result = generator.generate_pdf(all_front, all_back, output_file)

            messagebox.showinfo("Успех",
                                f"PDF успешно создан!\n"
                                f"Файл: {output_file}\n"
                                f"Листов: {result['total_sheets']}\n"
                                f"Визиток на листе: {result['cards_per_sheet']}\n"
                                f"Всего визиток: {total_cards}")

            self.status_var.set(f"PDF создан: {os.path.basename(output_file)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PDF: {str(e)}")
            self.status_var.set("Ошибка создания PDF")

    def clear_all(self):
        """Очистить все настройки"""
        self.clear_all_parties()
        self.config = PrintConfig()
        self.front_entry.configure(state='normal')
        self.front_entry.delete(0, tk.END)
        self.front_entry.configure(state='readonly')
        self.back_entry.configure(state='normal')
        self.back_entry.delete(0, tk.END)
        self.back_entry.configure(state='readonly')

        self.sheet_combo.set(self.config.sheet_size)
        self.card_combo.set(self.config.card_size)
        self.scheme_combo.set(self.config.matching_scheme)
        self.sheet_width_spin.set(self.config.custom_sheet_width)
        self.sheet_height_spin.set(self.config.custom_sheet_height)
        self.card_width_spin.set(self.config.custom_card_width)
        self.card_height_spin.set(self.config.custom_card_height)
        self.margin_spin.set(self.config.margin)
        self.bleed_spin.set(self.config.bleed)
        self.gutter_spin.set(self.config.gutter)
        self.mark_length_spin.set(self.config.mark_length)
        self.quantity_spin.set(1)
        self.rotate_var.set(self.config.rotate_cards)
        self.crop_var.set(self.config.add_crop_marks)
        self.fit_var.set(self.config.fit_proportions)
        self.match_var.set(self.config.match_by_name)

        self.update_custom_size_visibility()
        self.update_custom_sheet_visibility()
        self.update_preview()
        self.status_var.set("Все настройки очищены")


def main():
    root = tk.Tk()
    app = ImpositionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()