# -*- coding: utf-8 -*-
# gui/settings_panel.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from config import SHEET_SIZES, CARD_SIZES

logger = logging.getLogger(__name__)


class SettingsPanel:
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса панели настроек"""
        # Параметры печати
        print_frame = ttk.LabelFrame(self.parent, text="Параметры печати", padding=10)
        print_frame.grid(row=1, column=0, columnspan=3, sticky="we", pady=5)
        print_frame.columnconfigure(1, weight=1)

        self.setup_print_settings(print_frame)

        # Опции
        options_frame = ttk.Frame(print_frame)
        options_frame.grid(row=10, column=0, columnspan=3, sticky="w", pady=5)
        self.setup_options(options_frame)

        # Информация о раскладке
        info_frame = ttk.LabelFrame(self.parent, text="Информация о раскладке", padding=10)
        info_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=5)
        info_frame.columnconfigure(0, weight=1)

        self.info_text = scrolledtext.ScrolledText(info_frame, height=6, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky="we", pady=5)

        # Кнопки действий
        self.setup_action_buttons()

    def setup_print_settings(self, parent):
        """Настройка параметров печати"""
        row = 0

        # Размер листа
        ttk.Label(parent, text="Размер листа:").grid(row=row, column=0, sticky="w", pady=2)
        self.sheet_combo = ttk.Combobox(parent, values=list(SHEET_SIZES.keys()), width=15)
        self.sheet_combo.set(self.main_window.config.sheet_size)
        self.sheet_combo.grid(row=row, column=1, sticky="w", pady=2)
        self.sheet_combo.bind('<<ComboboxSelected>>', self.on_config_change)
        row += 1

        # Произвольный размер листа
        self.custom_sheet_frame = ttk.Frame(parent)
        self.custom_sheet_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        self.setup_custom_sheet(self.custom_sheet_frame)
        row += 1

        # Размер визитки
        ttk.Label(parent, text="Размер визитки:").grid(row=row, column=0, sticky="w", pady=2)
        self.card_combo = ttk.Combobox(parent, values=list(CARD_SIZES.keys()), width=20)
        self.card_combo.set(self.main_window.config.card_size)
        self.card_combo.grid(row=row, column=1, sticky="w", pady=2)
        self.card_combo.bind('<<ComboboxSelected>>', self.on_config_change)
        row += 1

        # Произвольный размер визитки
        self.custom_size_frame = ttk.Frame(parent)
        self.custom_size_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        self.setup_custom_card(self.custom_size_frame)
        row += 1

        # Остальные параметры
        settings = [
            ("Поля:", "margin", 0, 50, 1.0),
            ("Вылет под обрез:", "bleed", 0, 10, 1.0),
            ("Зазор между визитками:", "gutter", 0, 20, 1.0),
            ("Длина обрезных меток:", "mark_length", 1, 20, 1.0),
            ("Толщина меток:", "mark_thickness", 0.1, 2.0, 0.1)
        ]

        for label, attr, from_val, to_val, increment in settings:
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
            spinbox = ttk.Spinbox(parent, from_=from_val, to=to_val, width=5, increment=increment)
            spinbox.set(getattr(self.main_window.config, attr))
            spinbox.grid(row=row, column=1, sticky="w", pady=2)
            spinbox.bind('<KeyRelease>', self.on_config_change)
            spinbox.bind('<Return>', self.on_config_change)
            setattr(self, f"{attr}_spin", spinbox)

            ttk.Label(parent, text="мм").grid(row=row, column=2, sticky="w", pady=2)
            row += 1

        # Схема сопоставления
        ttk.Label(parent, text="Схема сопоставления:").grid(row=row, column=0, sticky="w", pady=2)
        self.scheme_combo = ttk.Combobox(parent, values=['1:1', '1:N', 'M:N'], width=10)
        self.scheme_combo.set(self.main_window.config.matching_scheme)
        self.scheme_combo.grid(row=row, column=1, sticky="w", pady=2)
        self.scheme_combo.bind('<<ComboboxSelected>>', self.on_config_change)
        row += 1

    def setup_custom_sheet(self, parent):
        """Настройка произвольного размера листа"""
        ttk.Label(parent, text="Ширина:").pack(side=tk.LEFT)
        self.sheet_width_spin = ttk.Spinbox(parent, from_=100, to=1000, width=5)
        self.sheet_width_spin.set(self.main_window.config.custom_sheet_width)
        self.sheet_width_spin.pack(side=tk.LEFT, padx=5)
        self.sheet_width_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(parent, text="Высота:").pack(side=tk.LEFT)
        self.sheet_height_spin = ttk.Spinbox(parent, from_=100, to=1000, width=5)
        self.sheet_height_spin.set(self.main_window.config.custom_sheet_height)
        self.sheet_height_spin.pack(side=tk.LEFT, padx=5)
        self.sheet_height_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(parent, text="мм").pack(side=tk.LEFT)

    def setup_custom_card(self, parent):
        """Настройка произвольного размера визитки"""
        ttk.Label(parent, text="Ширина:").pack(side=tk.LEFT)
        self.card_width_spin = ttk.Spinbox(parent, from_=10, to=200, width=5)
        self.card_width_spin.set(self.main_window.config.custom_card_width)
        self.card_width_spin.pack(side=tk.LEFT, padx=5)
        self.card_width_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(parent, text="Высота:").pack(side=tk.LEFT)
        self.card_height_spin = ttk.Spinbox(parent, from_=10, to=200, width=5)
        self.card_height_spin.set(self.main_window.config.custom_card_height)
        self.card_height_spin.pack(side=tk.LEFT, padx=5)
        self.card_height_spin.bind('<KeyRelease>', self.on_config_change)

        ttk.Label(parent, text="мм").pack(side=tk.LEFT)

    def setup_options(self, parent):
        """Настройка опций"""
        options = [
            ("rotate_var", "Поворачивать для экономии места", self.main_window.config.rotate_cards),
            ("crop_var", "Добавлять обрезные метки", self.main_window.config.add_crop_marks),
            ("fit_var", "Подгонка пропорций (fit)", self.main_window.config.fit_proportions),
            ("match_var", "Совпадение по именам", self.main_window.config.match_by_name)
        ]

        for var_name, text, default_value in options:
            var = tk.BooleanVar(value=default_value)
            cb = ttk.Checkbutton(parent, text=text, variable=var, command=self.on_config_change)
            cb.pack(side=tk.LEFT, padx=(0, 10))
            setattr(self, var_name, var)

    def setup_action_buttons(self):
        """Настройка кнопок действий"""
        button_frame = ttk.Frame(self.parent)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="Завершить и сгенерировать PDF",
                   command=self.generate_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить все партии",
                   command=self.clear_all_parties).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Очистить",
                   command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def on_config_change(self, event=None):
        """Обработчик изменения настроек"""
        self.update_config_from_ui()
        self.main_window.preview_panel.update_preview()

    def update_config_from_ui(self):
        """Обновить конфиг из UI"""
        try:
            config = self.main_window.config

            config.sheet_size = self.sheet_combo.get()
            config.custom_sheet = (config.sheet_size == 'Произвольный')

            if config.custom_sheet:
                config.custom_sheet_width = int(self.sheet_width_spin.get())
                config.custom_sheet_height = int(self.sheet_height_spin.get())

            config.card_size = self.card_combo.get()

            # Числовые параметры
            numeric_params = {
                'custom_card_width': self.card_width_spin,
                'custom_card_height': self.card_height_spin,
                'margin': self.margin_spin,
                'bleed': self.bleed_spin,
                'gutter': self.gutter_spin,
                'mark_length': self.mark_length_spin
            }

            for attr, widget in numeric_params.items():
                try:
                    setattr(config, attr, int(widget.get()))
                except ValueError:
                    pass

            # Параметры с плавающей точкой
            float_params = {
                'mark_thickness': self.mark_thickness_spin
            }
            for attr, widget in float_params.items():
                try:
                    setattr(config, attr, float(widget.get().replace(',', '.')))
                except ValueError:
                    pass

            config.matching_scheme = self.scheme_combo.get()

            # Булевы параметры
            config.rotate_cards = self.rotate_var.get()
            config.add_crop_marks = self.crop_var.get()
            config.fit_proportions = self.fit_var.get()
            config.match_by_name = self.match_var.get()

            self.update_visibility()
            logger.debug("Config updated from UI")

        except Exception as e:
            logger.error(f"Error updating config from UI: {e}")

    def update_visibility(self):
        """Обновить видимость элементов"""
        # Произвольный размер листа
        if self.main_window.config.custom_sheet:
            self.custom_sheet_frame.grid()
        else:
            self.custom_sheet_frame.grid_remove()

        # Произвольный размер визитки
        if self.main_window.config.card_size == 'Произвольный':
            self.custom_size_frame.grid()
        else:
            self.custom_size_frame.grid_remove()

    def update_layout_info(self, info_text):
        """Обновить информацию о раскладке"""
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_text)

    def generate_pdf(self):
        """Сгенерировать PDF"""
        from pdf_generator import PDFGenerator
        from tkinter import filedialog
        import os

        total_cards = self.main_window.get_total_cards()
        if total_cards == 0:
            self.main_window.show_error("Ошибка", "Нет визиток в партиях для генерации PDF")
            return

        output_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Сохранить PDF как"
        )

        if not output_file:
            return

        try:
            generator = PDFGenerator(self.main_window.config)

            # Сбор всех визиток из партий
            all_front = []
            all_back = []

            for party in self.main_window.parties:
                all_front.extend(party.front_images * party.quantity)
                if party.back_images:
                    # Сопоставляем обороты согласно схеме для каждой копии
                    num_designs = len(party.front_images)
                    for _ in range(party.quantity):
                        if self.main_window.config.matching_scheme == '1:1':
                            all_back.extend(party.back_images)
                        elif self.main_window.config.matching_scheme == '1:N':
                            all_back.extend([party.back_images[0]] * num_designs)
                        elif self.main_window.config.matching_scheme == 'M:N':
                            all_back.extend([party.back_images[i % len(party.back_images)] for i in range(num_designs)])
                else:
                    all_back.extend([None] * (len(party.front_images) * party.quantity))

            result = generator.generate_pdf(all_front, all_back, output_file)

            self.main_window.show_info("Успех",
                                       f"PDF успешно создан!\n"
                                       f"Файл: {output_file}\n"
                                       f"Листов: {result['total_sheets']}\n"
                                       f"Визиток на листе: {result['cards_per_sheet']}\n"
                                       f"Всего визиток: {total_cards}")

            self.main_window.update_status(f"PDF создан: {os.path.basename(output_file)}")
            logger.info(f"PDF generated: {output_file}, sheets: {result['total_sheets']}")

        except Exception as e:
            self.main_window.show_error("Ошибка", f"Не удалось создать PDF: {str(e)}")
            self.main_window.update_status("Ошибка создания PDF")
            logger.error(f"PDF generation error: {e}", exc_info=True)

    def clear_all_parties(self):
        """Очистить все партии"""
        self.main_window.clear_parties()
        self.main_window.file_selector.update_parties_display()
        self.main_window.preview_panel.update_preview()
        self.main_window.show_info("Очищено", "Все партии удалены")

    def clear_all(self):
        """Очистить все настройки"""
        self.clear_all_parties()

        # Сброс конфигурации
        self.main_window.config = type(self.main_window.config)()

        # Сброс UI элементов
        self.sheet_combo.set(self.main_window.config.sheet_size)
        self.card_combo.set(self.main_window.config.card_size)
        self.scheme_combo.set(self.main_window.config.matching_scheme)

        # Сброс спинбоксов
        spins = [
            (self.sheet_width_spin, self.main_window.config.custom_sheet_width),
            (self.sheet_height_spin, self.main_window.config.custom_sheet_height),
            (self.card_width_spin, self.main_window.config.custom_card_width),
            (self.card_height_spin, self.main_window.config.custom_card_height),
            (self.margin_spin, self.main_window.config.margin),
            (self.bleed_spin, self.main_window.config.bleed),
            (self.gutter_spin, self.main_window.config.gutter),
            (self.mark_length_spin, self.main_window.config.mark_length),
            (self.mark_thickness_spin, self.main_window.config.mark_thickness)
        ]

        for spin, value in spins:
            spin.set(value)

        # Сброс чекбоксов
        self.rotate_var.set(self.main_window.config.rotate_cards)
        self.crop_var.set(self.main_window.config.add_crop_marks)
        self.fit_var.set(self.main_window.config.fit_proportions)
        self.match_var.set(self.main_window.config.match_by_name)

        self.update_visibility()
        self.main_window.preview_panel.update_preview()
        self.main_window.update_status("Все настройки очищены")
        logger.info("All settings cleared")