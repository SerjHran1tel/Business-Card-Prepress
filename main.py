import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Главная функция приложения"""
    try:
        from gui import main as gui_main
        print("Запуск графического интерфейса...")
        gui_main()
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что установлены все зависимости:")
        print("pip install -r requirements.txt")
        input("Нажмите Enter для выхода...")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()