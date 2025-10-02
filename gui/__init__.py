# -*- coding: utf-8 -*-
# gui/__init__.py
from .main_window import MainWindow


def main():
    import tkinter as tk
    from utils.logger import setup_logging

    setup_logging()
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()