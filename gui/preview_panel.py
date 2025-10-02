# -*- coding: utf-8 -*-
# gui/preview_panel.py
import tkinter as tk
from tkinter import ttk
import logging
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os

logger = logging.getLogger(__name__)


class PreviewPanel:
    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.preview_width = 800
        self.preview_height = 500
        self.canvas = None
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса предпросмотра"""
        # Панель управления предпросмотром
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="Визуальный предпросмотр раскладки",
                  font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)

        # Переключатель отображения безопасной зоны
        self.show_safe_zone = tk.BooleanVar(value=True)
        safe_zone_cb = ttk.Checkbutton(
            control_frame,
            text="Показывать безопасную зону",
            variable=self.show_safe_zone,
            command=self.update_preview
        )
        safe_zone_cb.pack(side=tk.RIGHT, padx=10)

        # Переключатель отображения предупреждений
        self.show_warnings = tk.BooleanVar(value=True)
        warnings_cb = ttk.Checkbutton(
            control_frame,
            text="Показывать предупреждения",
            variable=self.show_warnings,
            command=self.update_preview
        )
        warnings_cb.pack(side=tk.RIGHT, padx=10)

        self.preview_container = ttk.Frame(self.parent)
        self.preview_container.pack(fill=tk.BOTH, expand=True, pady=10)
        self.preview_container.bind('<Configure>', self.on_container_resize)

    def on_container_resize(self, event):
        """Обработчик изменения размера контейнера предпросмотра"""
        new_width = event.width
        new_height = event.height
        if new_width > 0 and new_height > 0 and (new_width != self.preview_width or new_height != self.preview_height):
            self.preview_width = new_width
            self.preview_height = new_height
            self.update_preview()

    def handle_resize(self):
        """Обработчик изменения размера (для внешнего вызова)"""
        if hasattr(self, 'preview_container'):
            new_width = self.preview_container.winfo_width()
            new_height = self.preview_container.winfo_height()
            if new_width > 0 and new_height > 0 and (
                    new_width != self.preview_width or new_height != self.preview_height):
                self.preview_width = new_width
                self.preview_height = new_height
                self.update_preview()

    def update_preview(self):
        """Обновить предпросмотр"""
        # Очистка предыдущего предпросмотра
        for widget in self.preview_container.winfo_children():
            widget.destroy()

        total_cards = self.main_window.get_total_cards()
        current_front_count = len(self.main_window.front_images)

        # Если нет ни текущих изображений, ни партий, показать сообщение
        if total_cards == 0 and current_front_count == 0:
            ttk.Label(self.preview_container,
                      text="Выберите файлы и добавьте партию для предпросмотра\n(или нажмите 'Загрузить демо')",
                      font=("Arial", 10), foreground="orange").pack(pady=20)
            return

        # Получить параметры из конфига
        sheet_w, sheet_h = self.main_window.config.get_sheet_dimensions()
        card_w, card_h = self.main_window.config.get_card_dimensions()

        from layout_calculator import LayoutCalculator
        calculator = LayoutCalculator(
            sheet_w, sheet_h, card_w, card_h,
            self.main_window.config.margin, self.main_window.config.bleed,
            self.main_window.config.gutter, self.main_window.config.rotate_cards
        )

        layout = calculator.calculate_layout()

        if layout.cards_total == 0:
            ttk.Label(self.preview_container, text="Визитки не помещаются на лист!",
                      foreground="red").pack(pady=5)
            return

        # Создание фигуры matplotlib
        fig_width = max(8, self.preview_width / 100)
        fig_height = max(6, self.preview_height / 100)
        fig = Figure(figsize=(fig_width, fig_height), dpi=100)
        fig.suptitle("Предпросмотр раскладки (левый: передняя, правый: задняя)", fontsize=12)

        # Передняя сторона
        ax_front = fig.add_subplot(121)
        ax_front.set_xlim(0, sheet_w)
        ax_front.set_ylim(0, sheet_h)
        ax_front.set_aspect('equal')
        ax_front.invert_yaxis()
        ax_front.set_title("Передняя сторона")

        # Задняя сторона
        ax_back = fig.add_subplot(122)
        ax_back.set_xlim(0, sheet_w)
        ax_back.set_ylim(0, sheet_h)
        ax_back.set_aspect('equal')
        ax_back.invert_yaxis()

        if len(self.main_window.back_images) > 0:
            ax_back.set_title("Задняя сторона")
            # Подготовка изображений для задней стороны согласно схеме
            if self.main_window.config.matching_scheme != '1:1':
                if self.main_window.config.matching_scheme == '1:N':
                    back_images_preview = [self.main_window.back_images[0]] * len(self.main_window.front_images)
                elif self.main_window.config.matching_scheme == 'M:N':
                    back_images_preview = [self.main_window.back_images[i % len(self.main_window.back_images)] for i in
                                           range(len(self.main_window.front_images))]
            else:
                back_images_preview = self.main_window.back_images
        else:
            ax_back.set_title("Задняя сторона (отсутствует)")
            ax_back.text(0.5, 0.5, "Нет оборотных сторон\n(односторонняя печать)",
                         ha='center', va='center', transform=ax_back.transAxes,
                         fontsize=10, color='orange')
            back_images_preview = []

        # Отрисовка сетки и меток для обеих сторон
        for ax in [ax_front, ax_back]:
            # Прямоугольник листа
            sheet_rect = FancyBboxPatch((0, 0), sheet_w, sheet_h, boxstyle="round,pad=0.01",
                                        edgecolor='gray', facecolor='lightgray', alpha=0.1, linewidth=2)
            ax.add_patch(sheet_rect)
            ax.text(sheet_w / 2, -sheet_h * 0.05, 'Sheet (Margins)', ha='center', fontsize=8, color='gray',
                    transform=ax.transData)

            # Рабочая область
            work_x = self.main_window.config.margin
            work_y = self.main_window.config.margin
            work_w = sheet_w - 2 * self.main_window.config.margin
            work_h = sheet_h - 2 * self.main_window.config.margin
            work_rect = FancyBboxPatch((work_x, work_y), work_w, work_h, boxstyle="round,pad=0.005",
                                       edgecolor='blue', facecolor='lightblue', alpha=0.2, linewidth=1.5)
            ax.add_patch(work_rect)
            ax.text(work_x + work_w / 2, work_y - 5, 'Work Area', ha='center', fontsize=8, color='blue',
                    transform=ax.transData)

        # Отрисовка визиток для передней стороны
        self.draw_side(ax_front, self.main_window.front_images, layout, sheet_w, sheet_h)

        # Отрисовка визиток для задней стороны
        if back_images_preview:
            self.draw_side(ax_back, back_images_preview, layout, sheet_w, sheet_h)

        for ax in [ax_front, ax_back]:
            ax.axis('off')

        # Встраивание фигуры в Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.preview_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Текстовая информация о раскладке
        preview_text = f"""Лист: {sheet_w}×{sheet_h} мм
Визитки: {layout.cards_x}×{layout.cards_y} = {layout.cards_total} шт.
Поворот: {'Да' if layout.rotated else 'Нет'}
Эффективность: {layout.efficiency:.1%}"""

        # Добавляем информацию о проблемных зонах
        if self.show_warnings.get():
            warnings = self.get_layout_warnings(layout, sheet_w, sheet_h, card_w, card_h)
            if warnings:
                preview_text += f"\n\n⚠️ ПРЕДУПРЕЖДЕНИЯ:\n" + "\n".join([f"• {w}" for w in warnings])

        ttk.Label(self.preview_container, text=preview_text, font=("Courier", 9)).pack(pady=5)

    def draw_side(self, ax, images_list, layout, sheet_w, sheet_h):
        """Отрисовать одну сторону листа с визитками"""
        for i, pos in enumerate(layout.positions):
            if i >= len(images_list):
                break

            inner_x = pos['x'] + self.main_window.config.bleed
            inner_y = pos['y'] + self.main_window.config.bleed
            card_w, card_h = self.main_window.config.get_card_dimensions()

            # Область с вылетом под обрез
            bleed_rect = FancyBboxPatch((pos['x'], pos['y']), pos['width'], pos['height'],
                                        boxstyle="round,pad=0.005", edgecolor='green', facecolor='lightgreen',
                                        alpha=0.15, linewidth=1)
            ax.add_patch(bleed_rect)
            ax.text(pos['x'] + pos['width'] / 2, pos['y'] - 2, 'Bleed', ha='center', fontsize=7, color='green',
                    transform=ax.transData)

            # Внутренняя область визитки (без вылета)
            inner_rect = FancyBboxPatch((inner_x, inner_y), card_w, card_h, boxstyle="round,pad=0.005",
                                        edgecolor='black', facecolor='white', linewidth=1.5)
            ax.add_patch(inner_rect)
            ax.text(inner_x + card_w / 2, inner_y + card_h + 2, 'Card', ha='center', fontsize=7, color='black',
                    transform=ax.transData)

            # Безопасная зона
            if self.show_safe_zone.get():
                safe_zone_margin = 5  # мм от края визитки
                safe_x = inner_x + safe_zone_margin
                safe_y = inner_y + safe_zone_margin
                safe_w = card_w - 2 * safe_zone_margin
                safe_h = card_h - 2 * safe_zone_margin

                safe_rect = Rectangle((safe_x, safe_y), safe_w, safe_h,
                                      linewidth=1, edgecolor='red', facecolor='none',
                                      linestyle='--', alpha=0.7)
                ax.add_patch(safe_rect)
                ax.text(safe_x + safe_w / 2, safe_y - 2, 'Safe Zone', ha='center',
                        fontsize=6, color='red', transform=ax.transData)

            # Изображение визитки
            if i < len(images_list):
                try:
                    img_path = images_list[i]
                    img = Image.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    preview_scale = 2
                    img_resized = img.resize((int(card_w * preview_scale), int(card_h * preview_scale)),
                                             Image.Resampling.LANCZOS)
                    arr = np.array(img_resized)
                    im = OffsetImage(arr, zoom=1.0 / preview_scale)
                    ab = AnnotationBbox(im, (inner_x + card_w / 2, inner_y + card_h / 2),
                                        xybox=(0, 0), frameon=False, pad=0, boxcoords="offset points")
                    ax.add_artist(ab)
                except Exception as e:
                    logger.error(f"Ошибка загрузки изображения {img_path} для preview: {e}")

            # Обрезные метки
            if self.main_window.config.add_crop_marks:
                mark_len = self.main_window.config.mark_length
                ax.plot([inner_x, inner_x], [inner_y, inner_y + mark_len], 'k-', lw=0.5)
                ax.plot([inner_x, inner_x - mark_len], [inner_y, inner_y], 'k-', lw=0.5)
                ax.plot([inner_x + card_w, inner_x + card_w], [inner_y, inner_y + mark_len], 'k-', lw=0.5)
                ax.plot([inner_x + card_w, inner_x + card_w + mark_len], [inner_y, inner_y], 'k-', lw=0.5)
                ax.plot([inner_x, inner_x], [inner_y + card_h, inner_y + card_h - mark_len], 'k-', lw=0.5)
                ax.plot([inner_x, inner_x - mark_len], [inner_y + card_h, inner_y + card_h], 'k-', lw=0.5)
                ax.plot([inner_x + card_w, inner_x + card_w], [inner_y + card_h, inner_y + card_h - mark_len], 'k-',
                        lw=0.5)
                ax.plot([inner_x + card_w, inner_x + card_w + mark_len], [inner_y + card_h, inner_y + card_h], 'k-',
                        lw=0.5)

    def get_layout_warnings(self, layout, sheet_w, sheet_h, card_w, card_h):
        """Получить предупреждения о проблемных зонах раскладки"""
        warnings = []

        # Проверка эффективности использования площади
        if layout.efficiency < 0.6:
            warnings.append(f"Низкая эффективность использования площади: {layout.efficiency:.1%}")

        # Проверка границ
        for i, pos in enumerate(layout.positions):
            if pos['x'] < self.main_window.config.margin - 1:  # С запасом
                warnings.append(f"Визитка {i + 1} слишком близко к левому краю")
            if pos['x'] + pos['width'] > sheet_w - self.main_window.config.margin + 1:
                warnings.append(f"Визитка {i + 1} слишком близко к правому краю")
            if pos['y'] < self.main_window.config.margin - 1:
                warnings.append(f"Визитка {i + 1} слишком близко к верхнему краю")
            if pos['y'] + pos['height'] > sheet_h - self.main_window.config.margin + 1:
                warnings.append(f"Визитка {i + 1} слишком близко к нижнему краю")

        return warnings