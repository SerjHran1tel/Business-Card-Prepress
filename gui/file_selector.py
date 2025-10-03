# -*- coding: utf-8 -*-
# gui/file_selector.py
import tkinter as tk
from tkinter import ttk, filedialog
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
import logging
from image_utils import scan_images, validate_image_pairs, validate_image_pairs_extended, generate_validation_report, \
    get_image_info
from converter import convert_to_raster, check_conversion_dependencies, SUPPORTED_VECTOR_FORMATS

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

        # Информация о поддерживаемых форматах
        formats_info = ttk.Label(
            folder_frame,
            text="Поддерживаемые форматы: JPG, PNG, TIFF, BMP, WEBP, PDF, SVG",
            font=("Arial", 8),
            foreground="gray"
        )
        formats_info.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        # Лицевые стороны
        ttk.Label(folder_frame, text="Лицевые стороны:").grid(row=1, column=0, sticky="w", pady=2)
        self.front_entry = ttk.Entry(folder_frame)
        self.front_entry.grid(row=1, column=1, sticky="we", padx=5)
        self.front_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_front_files).grid(row=1, column=2)

        # Оборотные стороны
        ttk.Label(folder_frame, text="Оборотные стороны:").grid(row=2, column=0, sticky="w", pady=2)
        self.back_entry = ttk.Entry(folder_frame)
        self.back_entry.grid(row=2, column=1, sticky="we", padx=5)
        self.back_entry.configure(state='readonly')
        ttk.Button(folder_frame, text="Обзор", command=self.select_back_files).grid(row=2, column=2)

        # Количество копий
        ttk.Label(folder_frame, text="Количество копий:").grid(row=3, column=0, sticky="w", pady=2)
        self.quantity_spin = ttk.Spinbox(folder_frame, from_=1, to=10000, width=10)
        self.quantity_spin.set(self.main_window.current_quantity)
        self.quantity_spin.grid(row=3, column=1, sticky="w", pady=2)
        self.quantity_spin.bind('<KeyRelease>', self.on_quantity_change)

        # Кнопки управления
        button_frame = ttk.Frame(folder_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="Загрузить демо",
                   command=self.load_demo).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Добавить партию",
                   command=self.add_current_party).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить текущую",
                   command=self.clear_current_party).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Проверить качество",
                   command=self.validate_images).pack(side=tk.LEFT, padx=5)

        # Отображение партий
        parties_frame = ttk.Frame(folder_frame)
        parties_frame.grid(row=5, column=0, columnspan=3, sticky="we", pady=5)

        ttk.Label(parties_frame, text="Текущие партии:").pack(anchor="w")
        self.parties_text = tk.Text(parties_frame, height=4, wrap=tk.WORD, font=("Courier", 9))
        self.parties_text.pack(fill=tk.X, pady=5)

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
            filetypes=[
                ("Все поддерживаемые", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp *.pdf *.svg"),
                ("Растровые изображения", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"),
                ("Векторные форматы", "*.pdf *.svg"),
                ("PDF файлы", "*.pdf"),
                ("SVG файлы", "*.svg"),
                ("Все файлы", "*.*")
            ]
        )
        if files:
            self.main_window.config.front_files = list(files)
            self.update_file_display(self.front_entry, files)
            self.load_current_images()

    def select_back_files(self):
        """Выбор файлов оборотных сторон"""
        files = filedialog.askopenfilenames(
            title="Выберите файлы оборотных сторон",
            filetypes=[
                ("Все поддерживаемые", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp *.pdf *.svg"),
                ("Растровые изображения", "*.jpg *.jpeg *.png *.tiff *.bmp *.tif *.webp"),
                ("Векторные форматы", "*.pdf *.svg"),
                ("PDF файлы", "*.pdf"),
                ("SVG файлы", "*.svg"),
                ("Все файлы", "*.*")
            ]
        )
        if files:
            self.main_window.config.back_files = list(files)
            self.update_file_display(self.back_entry, files)
            self.load_current_images()

    def update_file_display(self, entry_widget, files):
        """Обновить отображение выбранных файлов"""
        if not files:
            display_text = ""
        elif len(files) == 1:
            display_text = os.path.basename(files[0])
        else:
            first_name = os.path.basename(files[0])
            display_text = f"{first_name} (и {len(files) - 1} других)"

        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, display_text)
        entry_widget.configure(state='readonly')

    def load_current_images(self):
        """Загрузить изображения для текущей партии"""
        self.main_window.front_images = []
        self.main_window.back_images = []
        conversion_errors = []
        conversion_warnings = []

        # Обработка лицевых сторон
        if self.main_window.config.front_files:
            for f in self.main_window.config.front_files:
                new_path, error = convert_to_raster(f)
                if error:
                    conversion_errors.append(f"{os.path.basename(f)}: {error}")
                if new_path != f:  # Если файл был сконвертирован
                    self.main_window.temp_files.append(new_path)
                self.main_window.front_images.append(new_path)

        # Обработка оборотных сторон
        if self.main_window.config.back_files:
            for f in self.main_window.config.back_files:
                new_path, error = convert_to_raster(f)
                if error:
                    conversion_errors.append(f"{os.path.basename(f)}: {error}")
                if new_path != f:  # Если файл был сконвертирован
                    self.main_window.temp_files.append(new_path)
                self.main_window.back_images.append(new_path)

        # Базовая валидация изображений
        self.validate_images_basic()

        # Показать ошибки
        if conversion_errors:
            self.main_window.show_error("Ошибки конвертации", "\n".join(conversion_errors))

        # Обновить статус
        front_count = len(self.main_window.front_images)
        back_count = len(self.main_window.back_images)
        status_text = f"Текущая партия: {front_count} лиц, {back_count} рубашек"

        # Добавить информацию о векторных файлах
        vector_count = sum(1 for f in self.main_window.config.front_files + self.main_window.config.back_files
                           if f.lower().endswith(SUPPORTED_VECTOR_FORMATS))
        if vector_count > 0:
            status_text += f" ({vector_count} векторных)"

        self.main_window.update_status(status_text)
        self.main_window.preview_panel.update_preview()

    def validate_images_basic(self):
        """Базовая валидация пар изображений"""
        front_info_list = []
        for p in self.main_window.front_images:
            try:
                img = Image.open(p)
                front_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': img.size})
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")
                front_info_list.append({'path': p, 'filename': os.path.basename(p), 'error': str(e)})

        back_info_list = []
        for p in self.main_window.back_images:
            try:
                img = Image.open(p)
                back_info_list.append({'path': p, 'filename': os.path.basename(p), 'size': img.size})
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")
                back_info_list.append({'path': p, 'filename': os.path.basename(p), 'error': str(e)})

        errors, warnings = validate_image_pairs(
            front_info_list, back_info_list,
            self.main_window.config.matching_scheme,
            self.main_window.config.match_by_name
        )

        if errors:
            self.main_window.show_error("Ошибки валидации", "\n".join(errors))
        if warnings:
            self.main_window.show_warning("Предупреждения валидации", "\n".join(warnings))

    def validate_images(self):
        """Расширенная валидация пар изображений с проверкой качества"""
        if not self.main_window.front_images and not self.main_window.back_images:
            self.main_window.show_warning("Проверка качества", "Нет изображений для проверки")
            return

        front_info_list = []
        for p in self.main_window.front_images:
            try:
                info = get_image_info(p)
                front_info_list.append(info)
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")
                front_info_list.append({
                    'path': p,
                    'filename': os.path.basename(p),
                    'error': str(e)
                })

        back_info_list = []
        for p in self.main_window.back_images:
            try:
                info = get_image_info(p)
                back_info_list.append(info)
            except Exception as e:
                logger.error(f"Error loading image {p}: {e}")
                back_info_list.append({
                    'path': p,
                    'filename': os.path.basename(p),
                    'error': str(e)
                })

        # Используем расширенную валидацию
        card_width, card_height = self.main_window.config.get_card_dimensions()
        validation_result = validate_image_pairs_extended(
            front_info_list, back_info_list,
            self.main_window.config.matching_scheme,
            self.main_window.config.match_by_name,
            card_width,
            card_height,
            self.main_window.config.bleed
        )

        # Генерируем детальный отчет
        report = generate_validation_report(validation_result)

        # Показываем отчет в отдельном окне
        self.show_validation_report(report)

    def show_validation_report(self, report):
        """Показать детальный отчет о валидации"""
        report_window = tk.Toplevel(self.parent)
        report_window.title("Отчет о проверке качества изображений")
        report_window.geometry("700x500")
        report_window.minsize(600, 400)

        # Заголовок
        header_frame = ttk.Frame(report_window)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(header_frame, text="Результаты проверки качества изображений",
                  font=("Arial", 12, "bold")).pack(pady=5)

        ttk.Label(header_frame, text="Детальный анализ DPI, цветовых профилей и безопасных зон",
                  font=("Arial", 9), foreground="gray").pack()

        # Основное содержимое
        content_frame = ttk.Frame(report_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Создаем текстовое поле с прокруткой
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 9), padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Вставляем отчет с цветовым форматированием
        text_widget.insert(tk.END, report)

        # Настраиваем теги для цветового форматирования
        text_widget.tag_configure("error", foreground="red", font=("Courier", 9, "bold"))
        text_widget.tag_configure("warning", foreground="orange", font=("Courier", 9, "bold"))
        text_widget.tag_configure("dpi", foreground="purple", font=("Courier", 9))
        text_widget.tag_configure("color", foreground="blue", font=("Courier", 9))
        text_widget.tag_configure("safe_zone", foreground="brown", font=("Courier", 9))
        text_widget.tag_configure("info", foreground="green", font=("Courier", 9))
        text_widget.tag_configure("success", foreground="darkgreen", font=("Courier", 9, "bold"))

        # Применяем цветовое форматирование
        self.apply_text_formatting(text_widget, report)

        text_widget.configure(state=tk.DISABLED)

        # Кнопки
        button_frame = ttk.Frame(report_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Закрыть",
                   command=report_window.destroy).pack(side=tk.RIGHT, padx=5)

        ttk.Button(button_frame, text="Сохранить отчет",
                   command=lambda: self.save_validation_report(report)).pack(side=tk.RIGHT, padx=5)

    def apply_text_formatting(self, text_widget, report):
        """Применить цветовое форматирование к тексту отчета"""
        lines = report.split('\n')

        for line_num, line in enumerate(lines, 1):
            start_pos = f"{line_num}.0"
            end_pos = f"{line_num}.end"

            if line.startswith("🚨 ОШИБКИ:"):
                text_widget.tag_add("error", start_pos, end_pos)
            elif line.startswith("⚠️ ПРЕДУПРЕЖДЕНИЯ:"):
                text_widget.tag_add("warning", start_pos, end_pos)
            elif line.startswith("📏 ПРОБЛЕМЫ С РАЗРЕШЕНИЕМ:"):
                text_widget.tag_add("dpi", start_pos, end_pos)
            elif line.startswith("🎨 ПРОБЛЕМЫ С ЦВЕТОМ:"):
                text_widget.tag_add("color", start_pos, end_pos)
            elif line.startswith("🛡️ ПРОБЛЕМЫ БЕЗОПАСНОЙ ЗОНЫ:"):
                text_widget.tag_add("safe_zone", start_pos, end_pos)
            elif line.startswith("ℹ️ ИНФОРМАЦИЯ:"):
                text_widget.tag_add("info", start_pos, end_pos)
            elif line.startswith("✅ Все проверки пройдены успешно!"):
                text_widget.tag_add("success", start_pos, end_pos)
            elif line.startswith("  •"):
                # Определяем категорию для пунктов списка
                categories = [
                    ("🚨 ОШИБКИ:", "error"),
                    ("⚠️ ПРЕДУПРЕЖДЕНИЯ:", "warning"),
                    ("📏 ПРОБЛЕМЫ С РАЗРЕШЕНИЕМ:", "dpi"),
                    ("🎨 ПРОБЛЕМЫ С ЦВЕТОМ:", "color"),
                    ("🛡️ ПРОБЛЕМЫ БЕЗОПАСНОЙ ЗОНЫ:", "safe_zone")
                ]

                for category, tag in categories:
                    category_pos = report.find(category)
                    line_pos = report.find(line)
                    if category_pos != -1 and line_pos > category_pos:
                        text_widget.tag_add(tag, start_pos, end_pos)
                        break

    def save_validation_report(self, report):
        """Сохранить отчет о валидации в файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Сохранить отчет о проверке"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("ОТЧЕТ О ПРОВЕРКЕ КАЧЕСТВА ИЗОБРАЖЕНИЙ\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(report)

                self.main_window.show_info("Успех", f"Отчет сохранен в файл:\n{filename}")
            except Exception as e:
                self.main_window.show_error("Ошибка", f"Не удалось сохранить отчет: {e}")

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
        text = ""
        total_cards = self.main_window.get_total_cards()

        if not self.main_window.parties:
            text = "Партии не добавлены\n"
        else:
            for i, party in enumerate(self.main_window.parties, 1):
                num_designs = len(party.front_images)
                back_info = f", {len(party.back_images)} об." if party.back_images else ""
                text += f"Партия {i}: {num_designs} дизайнов{back_info} × {party.quantity} копий = {party.total_cards} визиток\n"

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

            # Создаем демо-изображения разных размеров для тестирования
            demo_sizes = [(900, 500), (850, 550), (800, 400), (950, 450), (880, 520)]

            for i, size in enumerate(demo_sizes):
                # Лицевые стороны
                temp_front = tempfile.NamedTemporaryFile(suffix=f'_front_{i + 1}.png', delete=False)
                img_front = Image.new('RGB', size, color=(i * 50, 100, 200))
                # Добавляем текст для наглядности
                draw = ImageDraw.Draw(img_front)
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
                draw.text((50, 50), f"Front {i + 1}", fill=(255, 255, 255), font=font)
                img_front.save(temp_front.name)
                front_temp_files.append(temp_front.name)
                self.main_window.config.front_files.append(temp_front.name)
                self.main_window.temp_files.append(temp_front.name)

                # Оборотные стороны
                temp_back = tempfile.NamedTemporaryFile(suffix=f'_back_{i + 1}.png', delete=False)
                img_back = Image.new('RGB', size, color=(200, 100, i * 50))
                draw = ImageDraw.Draw(img_back)
                draw.text((50, 50), f"Back {i + 1}", fill=(255, 255, 255), font=font)
                img_back.save(temp_back.name)
                back_temp_files.append(temp_back.name)
                self.main_window.config.back_files.append(temp_back.name)
                self.main_window.temp_files.append(temp_back.name)

            self.update_file_display(self.front_entry, front_temp_files)
            self.update_file_display(self.back_entry, back_temp_files)

            self.load_current_images()
            logger.info("Demo images loaded successfully")
            self.main_window.show_info("Демо загружено", "5 демо-изображений успешно загружены")

        except Exception as e:
            self.main_window.show_error("Ошибка демо", f"Не удалось создать демо: {e}")
            logger.error(f"Demo loading error: {e}")