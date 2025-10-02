# -*- coding: utf-8 -*-
# gui/main_window.py
import tkinter as tk
from tkinter import ttk
import logging
from gui.preview_panel import PreviewPanel
from gui.file_selector import FileSelector
from gui.settings_panel import SettingsPanel
from config import PrintConfig
from core.models import Party

logger = logging.getLogger(__name__)

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Визиточный импозер v2.0")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)

        self.config = PrintConfig()
        self.parties = []
        self.current_quantity = 1
        self.front_images = []
        self.back_images = []
        self.temp_files = []

        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Основная вкладка
        self.main_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.main_frame, text="Основные настройки")

        # Вкладка предпросмотра
        self.preview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_frame, text="Предпросмотр")

        # Инициализация компонентов
        self.file_selector = FileSelector(self.main_frame, self)
        self.settings_panel = SettingsPanel(self.main_frame, self)
        self.preview_panel = PreviewPanel(self.preview_frame, self)

        # Статус бар
        self.setup_status_bar()

    def setup_status_bar(self):
        """Настройка статусной строки"""
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def setup_bindings(self):
        """Настройка привязок событий"""
        self.root.bind('<Configure>', self.on_resize)

    def on_resize(self, event):
        """Обработчик изменения размера окна"""
        if event.widget == self.root:
            self.preview_panel.handle_resize()

    def add_party(self, front_images, back_images, quantity):
        """Добавить партию"""
        party = Party(
            front_images=front_images.copy(),
            back_images=back_images.copy(),
            quantity=quantity
        )
        self.parties.append(party)
        logger.info(f"Added party: {len(front_images)} designs × {quantity} copies")

    def clear_parties(self):
        """Очистить все партии"""
        self.parties.clear()
        logger.info("All parties cleared")

    def get_total_cards(self):
        """Получить общее количество визиток"""
        return sum(party.total_cards for party in self.parties)

    def update_status(self, message):
        """Обновить статус"""
        self.status_var.set(message)
        logger.info(f"Status updated: {message}")

    def show_error(self, title, message):
        """Показать ошибку"""
        from tkinter import messagebox
        messagebox.showerror(title, message)
        logger.error(f"{title}: {message}")

    def show_info(self, title, message):
        """Показать информацию"""
        from tkinter import messagebox
        messagebox.showinfo(title, message)
        logger.info(f"{title}: {message}")

    def show_warning(self, title, message):
        """Показать предупреждение"""
        from tkinter import messagebox
        messagebox.showwarning(title, message)
        logger.warning(f"{title}: {message}")