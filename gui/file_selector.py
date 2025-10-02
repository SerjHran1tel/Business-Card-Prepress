# -*- coding: utf-8 -*-
# gui/file_selector.py
import tkinter as tk
from tkinter import ttk, filedialog
import os
import tempfile
from PIL import Image
import logging
from image_utils import scan_images, validate_image_pairs
from converter import convert_to_raster

logger = logging.getLogger(__name__)


class FileSelector:
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса выбора файлов"""
        folder_frame = ttk.LabelFrame(self.parent, text="Файлы изображений", padding=10)
        folder_frame.grid(row=0, column=0, columnspan=3, sticky="we", pady=5)
        folder_frame.columnconfigure(1, weight=1)

        # Лицевые стороны
        ttk.Label(folder_frame, text="Лицевые стороны (multiple OK):").grid(row=0, column=0, sticky="w", pady=2)
        self.front_entry = ttk.Entry(folder_frame)
        self.front_entry.grid(row=0, column=1, sticky="we", padx=5)
        self.front_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_front_files).grid(row=0, column=2)

        # Оборотные стороны
        ttk.Label(folder_frame, text="Оборотные стороны (multiple OK):").grid(row=1, column=0, sticky="w", pady=2)
        self.back_entry = ttk.Entry(folder_frame)
        self.back_entry.grid(row=1, column=1, sticky="we", padx=5)
        self.back_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_back_files).grid(row=1, column=2)

        # Количество копий
        ttk.Label(folder_frame, text="Количество копий:").grid(row=2, column=0, sticky="w", pady=2)
        self.quantity_spin = ttk.Spinbox(folder_frame, from_=1, to=10000, width=10)
        self.quantity_spin.set(self.main_window.current_quantity)
        self.quantity_spin.grid(row=2, column=1, sticky="w", pady=2)
        self.quantity_spin.bind('<KeyRelease>', self.on_quantity_change)

        # Кнопки управления
        button_frame = ttk.Frame(folder_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=5)

        ttk.Button(button_frame, text="Загрузить демо",
                   command=self.load_demo).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Добавить партию",
                   command=self.add_current_party).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить текущую",
                   command=self.clear_current_party).pack(side=tk.LEFT, padx=5)

        # Отображение партий
        self.parties_text = tk.Text(folder_frame, height=4, width=80, wrap=tk.WORD)
        self.parties_text.grid(row=4, column=0, columnspan=3, sticky="we", pady=5)

    def on_quantity_change(self, event=None):
        """Обработчик изменения количества"""
        try:
            self.main_window.current_quantity = int(self.quantity_spin.get())
            self.main_window.preview_panel.update_preview()
        except ValueError:
            pass

    def select_front_files(self):
        """Выбор файлов лицевых сторон"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы лицевых сторон",
            filetypes=[("Все поддерживаемые", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp *.pdf"), ("Все файлы", "*.*")]
        )
        if files:
            self.main_window.config.front_files = list(files)
            self.update_file_display(self.front_entry, files)
            self.load_current_images()

    def select_back_files(self):
        """Выбор файлов оборотных сторон"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы оборотных сторон",
            filetypes=[("Все поддерживаемые", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp *.pdf"), ("Все файлы", "*.*")]
        )
        if files:
            self.main_window.config.back_files = list(files)
            self.update_file_display(self.back_entry, files)
            self.load_current_images()

    def update_file_display(self, entry_widget, files):
        """Обновить отображение выбранных файлов"""
        first_name = os.path.basename(files[0])
        display_text = first_name if len(files) == 1 else f"{first_name} (и {len(files) - 1} других)"
        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, display_text)
        entry_widget.configure(state='readonly')

    def load_current_images(self):
        """Загрузить изображения для текущей партии"""
        self.main_window.front_images = []
        self.main_window.back_images = []
        conversion_errors = []

        if self.main_window.config.front_files:
            for f in self.main_window.config.front_files:
                new_path, error = convert_to_raster(f)
                if error:
                    conversion_errors.append(error)
                if new_path != f: # Если файл был сконвертирован
                    self.main_window.temp_files.append(new_path)
                self.main_window.front_images.append(new_path)

        if self.main_window.config.back_files:
            for f in self.main_window.config.back_files:
                new_path, error = convert_to_raster(f)
                if error:
                    conversion_errors.append(error)
                if new_path != f: # Если файл был сконвертирован
                    self.main_window.temp_files.append(new_path)
                self.main_window.back_images.append(new_path)

        # Валидация изображений
        self.validate_images()

        if conversion_errors:
            self.main_window.show_error("Ошибки конвертации", "\n".join(conversion_errors))

        self.main_window.update_status(
            f"Текущая партия: {len(self.main_window.front_images)} лиц, {len(self.main_window.back_images)} рубашек")
        self.main_window.preview_panel.update_preview()

    def validate_images(self):
        """Валидация пар изображений"""
        front_info_list = []
        for p in self.main_window.front_images:
            try:
                front_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': Image.open(p).size})
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")

        back_info_list = []
        for p in self.main_window.back_images:
            try:
                back_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': Image.open(p).size})
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")

        errors, warnings = validate_image_pairs(
            front_info_list, back_info_list,
            self.main_window.config.matching_scheme,
            self.main_window.config.match_by_name
        )

        if errors:
            self.main_window.show_error("Ошибки", "\n".join(errors))
        if warnings:
            self.main_window.show_warning("Предупреждения", "\n".join(warnings))

    def add_current_party(self):
        """Добавить текущую партию"""
        if not self.main_window.front_images:
            self.main_window.show_error("Ошибка", "Выберите файлы для партии!")
            return

        self.main_window.add_party(
            self.main_window.front_images,
            self.main_window.back_images,
            self.main_window.current_quantity
        )

        self.clear_current_party()
        self.update_parties_display()
        self.main_window.preview_panel.update_preview()

        self.main_window.show_info("Успех", "Партия успешно добавлена")

    def clear_current_party(self):
        """Очистить текущую партию"""
        self.main_window.front_images = []
        self.main_window.back_images = []
        self.main_window.current_quantity = 1
        self.quantity_spin.set(1)

        self.front_entry.configure(state='normal')
        self.front_entry.delete(0, tk.END)
        self.front_entry.configure(state='readonly')

        self.back_entry.configure(state='normal')
        self.back_entry.delete(0, tk.END)
        self.back_entry.configure(state='readonly')

        self.main_window.preview_panel.update_preview()

    def update_parties_display(self):
        """Обновить отображение списка партий"""
        text = "Партии:\n"
        total_cards = self.main_window.get_total_cards()

        for i, party in enumerate(self.main_window.parties, 1):
            num_designs = len(party.front_images)
            text += f"Партия {i}: {num_designs} дизайнов × {party.quantity} копий = {party.total_cards} визиток\n"

        text += f"\nОбщее количество визиток: {total_cards}"
        self.parties_text.delete(1.0, tk.END)
        self.parties_text.insert(1.0, text)

    def load_demo(self):
        """Загрузить демо-изображения"""
        try:
            self.main_window.config.front_files = []
            self.main_window.config.back_files = []

            front_temp_files = []
            back_temp_files = []

            for i in range(5):
                # Создание демо-изображений
                temp_front = tempfile.NamedTemporaryFile(suffix=f'_front_{i + 1}.png', delete=False)
                img_front = Image.new('RGB', (900, 500), color=(i * 50, 100, 200))
                img_front.save(temp_front.name)
                front_temp_files.append(temp_front.name)
                self.main_window.config.front_files.append(temp_front.name)
                self.main_window.temp_files.append(temp_front.name)


                temp_back = tempfile.NamedTemporaryFile(suffix=f'_back_{i + 1}.png', delete=False)
                img_back = Image.new('RGB', (900, 500), color=(200, 100, i * 50))
                img_back.save(temp_back.name)
                back_temp_files.append(temp_back.name)
                self.main_window.config.back_files.append(temp_back.name)
                self.main_window.temp_files.append(temp_back.name)

            self.update_file_display(self.front_entry, front_temp_files)
            self.update_file_display(self.back_entry, back_temp_files)

            self.load_current_images()
            logger.info("Demo images loaded successfully")

        except Exception as e:
            self.main_window.show_error("Ошибка демо", f"Не удалось создать демо: {e}")
            logger.error(f"Demo loading error: {e}")