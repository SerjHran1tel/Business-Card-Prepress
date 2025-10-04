"""
Flask Web Interface для Business Card Imposition System
"""

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import base64
from io import BytesIO
import logging
from threading import Thread

# Импорт основного приложения
import sys
sys.path.append(os.path.dirname(__file__))

from imposition import (
    ImpositionApp, PageFormat, CardSize, MatchingMode, ColorMode,
    PrintSettings, FileManager, CardQuantity
)
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Директории
UPLOAD_FOLDER = Path('/app/uploads')
OUTPUT_FOLDER = Path('/app/output')
UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'eps'}

# Хранилище прогресса
progress_store = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_progress(session_id, stage, progress, message=""):
    """Обновление прогресса обработки"""
    if session_id not in progress_store:
        progress_store[session_id] = {}

    progress_store[session_id] = {
        'stage': stage,
        'progress': progress,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }

    # Автоочистка старых записей
    cleanup_old_progress()

def cleanup_old_progress():
    """Очистка старых записей прогресса"""
    cutoff_time = datetime.now() - timedelta(hours=1)
    to_remove = []

    for session_id, data in progress_store.items():
        if datetime.fromisoformat(data['timestamp']) < cutoff_time:
            to_remove.append(session_id)

    for session_id in to_remove:
        del progress_store[session_id]

def image_to_base64(image_path: Path, max_size=(200, 200)) -> str | None:
    """Конвертирует изображение в base64 для превью"""
    try:
        if image_path.suffix.lower() == '.pdf':
            # Пытаемся сконвертировать PDF в изображение
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(str(image_path), first_page=1, last_page=1, dpi=100)
                if images:
                    img = images[0]
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    img_str = base64.b64encode(buffer.getvalue()).decode()
                    return f"data:image/png;base64,{img_str}"
            except ImportError:
                logger.warning("pdf2image не установлен, PDF превью недоступно")
            return None
        else:
            img = Image.open(image_path)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"
    except Exception as e:
        logger.error(f"Ошибка создания превью {image_path}: {e}")
        return None

def validate_uploaded_file(file) -> tuple[bool, str]:
    """Валидация загружаемого файла"""
    try:
        # Проверка расширения
        if not allowed_file(file.filename):
            return False, f"Неподдерживаемый формат файла: {file.filename}"

        # Проверка размера
        file.seek(0, 2)  # Перемещаемся в конец файла
        file_size = file.tell()
        file.seek(0)  # Возвращаемся в начало

        if file_size > 50 * 1024 * 1024:  # 50MB
            return False, f"Файл слишком большой: {file.filename} ({file_size/1024/1024:.1f}MB)"

        if file_size == 0:
            return False, f"Файл пустой: {file.filename}"

        return True, "OK"

    except Exception as e:
        return False, f"Ошибка валидации файла: {str(e)}"

def background_processing(session_id, front_dir, back_dir, settings_data, quantities):
    """Фоновая обработка файлов"""
    try:
        # Инициализация хранилища прогресса
        if session_id not in progress_store:
            progress_store[session_id] = {}

        update_progress(session_id, "initializing", 5, "Инициализация обработки...")

        # Проверка существования директорий
        if not front_dir.exists():
            progress_store[session_id].update({
                'error': f'Директория лицевых сторон не найдена: {front_dir}',
                'success': False
            })
            return

        if not back_dir.exists() and settings_data.get('matching_mode') != 'one_to_many':
            progress_store[session_id].update({
                'error': f'Директория оборотных сторон не найдена: {back_dir}',
                'success': False
            })
            return

        imposition = ImpositionApp()

        update_progress(session_id, "configuring", 20, "Настройка параметров...")

        page_format_name = settings_data.get('page_format', 'A4')
        card_size_name = settings_data.get('card_size', 'Standard RU')
        matching_mode = settings_data.get('matching_mode', 'one_to_one')
        strict_matching = settings_data.get('strict_matching', True)

        page_formats = PageFormat.get_standard_formats()
        if page_format_name == 'custom':
            imposition.settings.page_format = PageFormat(
                'Custom',
                float(settings_data.get('custom_page_width', 210)),
                float(settings_data.get('custom_page_height', 297))
            )
        else:
            imposition.settings.page_format = page_formats.get(page_format_name, page_formats['A4'])

        card_sizes = CardSize.get_standard_sizes()
        if card_size_name == 'custom':
            imposition.settings.card_size = CardSize(
                float(settings_data.get('custom_card_width', 90)),
                float(settings_data.get('custom_card_height', 50))
            )
        else:
            imposition.settings.card_size = card_sizes.get(card_size_name, card_sizes['Standard RU'])

        # Дополнительные настройки
        imposition.settings.margin_top = float(settings_data.get('margin_top', 10))
        imposition.settings.margin_bottom = float(settings_data.get('margin_bottom', 10))
        imposition.settings.margin_left = float(settings_data.get('margin_left', 10))
        imposition.settings.margin_right = float(settings_data.get('margin_right', 10))
        imposition.settings.bleed = float(settings_data.get('bleed', 3))
        imposition.settings.gap = float(settings_data.get('gap', 2))
        imposition.settings.crop_marks = settings_data.get('crop_marks', True)
        imposition.settings.matching_mode = MatchingMode(matching_mode)
        imposition.settings.strict_name_matching = strict_matching
        imposition.settings.dpi = int(settings_data.get('dpi', 300))
        imposition.settings.output_dpi = int(settings_data.get('output_dpi', 300))

        # Настройка цветового режима
        color_mode = settings_data.get('color_mode', 'rgb')
        imposition.settings.color_mode = ColorMode(color_mode)

        # Валидация файлов
        update_progress(session_id, "validating", 30, "Проверка файлов...")

        validation = FileManager.validate_files(
            front_dir, back_dir, imposition.settings.matching_mode, strict_matching
        )

        if not validation.is_valid:
            progress_store[session_id].update({
                'error': validation.get_report(),
                'success': False
            })
            return

        # Формирование списков файлов
        update_progress(session_id, "preparing", 50, "Подготовка файлов...")

        front_files = FileManager.scan_directory(front_dir)
        front_cards = []
        for file in front_files:
            qty = quantities.get('front', {}).get(file.name, 1)
            front_cards.append(CardQuantity(file, qty))

        back_cards = None
        if back_dir.exists():
            back_files = FileManager.scan_directory(back_dir)
            if back_files:
                back_cards = []
                if matching_mode == 'one_to_many':
                    total_front = sum(c.quantity for c in front_cards)
                    back_cards.append(CardQuantity(back_files[0], total_front))
                else:
                    matches = FileManager.match_files(front_files, back_files, strict_matching)
                    for front_file in front_files:
                        back_file = matches.get(front_file)
                        if back_file:
                            qty = quantities.get('front', {}).get(front_file.name, 1)
                            back_cards.append(CardQuantity(back_file, qty))

        # Генерация PDF
        update_progress(session_id, "generating", 70, "Создание PDF...")

        output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
        success = imposition.process(front_cards, back_cards, str(output_file))

        if success:
            update_progress(session_id, "complete", 100, "Готово!")
            progress_store[session_id].update({
                'download_url': f'/download/{session_id}_imposition.pdf',
                'validation_report': validation.get_report(),
                'success': True
            })
        else:
            progress_store[session_id].update({
                'error': 'Ошибка при создании PDF',
                'success': False
            })

    except Exception as e:
        logger.error(f"Ошибка фоновой обработки: {e}")
        progress_store[session_id].update({
            'error': str(e),
            'success': False
        })

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Загрузка файлов"""
    try:
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        session_dir = UPLOAD_FOLDER / session_id
        front_dir = session_dir / 'front'
        back_dir = session_dir / 'back'

        front_dir.mkdir(parents=True, exist_ok=True)
        back_dir.mkdir(parents=True, exist_ok=True)

        front_files = request.files.getlist('front_files')
        back_files = request.files.getlist('back_files')

        if not front_files or front_files[0].filename == '':
            return jsonify({'error': 'Не загружены файлы лицевой стороны'}), 400

        # Валидация и сохранение лицевых сторон
        front_file_info = []
        for file in front_files:
            if file and allowed_file(file.filename):
                is_valid, message = validate_uploaded_file(file)
                if not is_valid:
                    return jsonify({'error': message}), 400

                filename = secure_filename(file.filename)
                file_path = front_dir / filename
                file.save(file_path)

                preview = image_to_base64(file_path)
                front_file_info.append({
                    'name': filename,
                    'preview': preview
                })

        # Валидация и сохранение оборотных сторон
        back_file_info = []
        if back_files and back_files[0].filename != '':
            for file in back_files:
                if file and allowed_file(file.filename):
                    is_valid, message = validate_uploaded_file(file)
                    if not is_valid:
                        return jsonify({'error': message}), 400

                    filename = secure_filename(file.filename)
                    file_path = back_dir / filename
                    file.save(file_path)

                    preview = image_to_base64(file_path)
                    back_file_info.append({
                        'name': filename,
                        'preview': preview
                    })

        logger.info(f"Загружены файлы для сессии {session_id}")
        return jsonify({
            'session_id': session_id,
            'front_files': front_file_info,
            'back_files': back_file_info
        }), 200

    except Exception as e:
        logger.error(f"Ошибка загрузки файлов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_imposition():
    """Запуск обработки в фоновом режиме"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Не указан session_id'}), 400

        session_dir = UPLOAD_FOLDER / session_id
        if not session_dir.exists():
            return jsonify({'error': 'Сессия не найдена'}), 404

        # Запускаем в фоне
        thread = Thread(
            target=background_processing,
            args=(
                session_id,
                session_dir / 'front',
                session_dir / 'back',
                data,
                data.get('quantities', {})
            )
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Обработка запущена в фоновом режиме'
        }), 200

    except Exception as e:
        logger.error(f"Ошибка запуска обработки: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<session_id>')
def get_progress(session_id):
    """Получение прогресса обработки"""
    progress_data = progress_store.get(session_id, {})
    return jsonify(progress_data)

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание готового файла"""
    file_path = OUTPUT_FOLDER / filename
    if file_path.exists():
        logger.info(f"Скачивание файла: {filename}")
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Файл не найден'}), 404

@app.route('/preview', methods=['POST'])
def preview():
    """Предварительный просмотр раскладки"""
    try:
        data = request.json
        session_id = data.get('session_id')

        settings = PrintSettings(
            page_format=PageFormat('A4', 210, 297),
            card_size=CardSize(90, 50)
        )

        # Применяем параметры из запроса
        page_format_name = data.get('page_format', 'A4')
        if page_format_name != 'custom':
            formats = PageFormat.get_standard_formats()
            settings.page_format = formats[page_format_name]
        else:
            settings.page_format = PageFormat(
                'Custom',
                float(data.get('custom_page_width', 210)),
                float(data.get('custom_page_height', 297))
            )

        card_size_name = data.get('card_size', 'Standard RU')
        if card_size_name != 'custom':
            sizes = CardSize.get_standard_sizes()
            settings.card_size = sizes[card_size_name]
        else:
            settings.card_size = CardSize(
                float(data.get('custom_card_width', 90)),
                float(data.get('custom_card_height', 50))
            )

        settings.margin_top = float(data.get('margin_top', 10))
        settings.margin_bottom = float(data.get('margin_bottom', 10))
        settings.margin_left = float(data.get('margin_left', 10))
        settings.margin_right = float(data.get('margin_right', 10))
        settings.gap = float(data.get('gap', 2))

        from imposition import LayoutCalculator
        cols, rows, x_offset, y_offset = LayoutCalculator.calculate_layout(settings)

        # Превью файлов
        front_previews = []
        back_previews = []

        if session_id:
            session_dir = UPLOAD_FOLDER / session_id
            front_dir = session_dir / 'front'
            back_dir = session_dir / 'back'

            if front_dir.exists():
                front_files = FileManager.scan_directory(front_dir)
                for file in front_files[:12]:
                    preview = image_to_base64(file)
                    front_previews.append({
                        'name': file.name,
                        'preview': preview
                    })

            if back_dir.exists():
                back_files = FileManager.scan_directory(back_dir)
                for file in back_files[:12]:
                    preview = image_to_base64(file)
                    back_previews.append({
                        'name': file.name,
                        'preview': preview
                    })

        logger.info(f"Сгенерирован превью для сессии {session_id}")
        return jsonify({
            'cols': cols,
            'rows': rows,
            'cards_per_sheet': cols * rows,
            'card_width': settings.card_size.width,
            'card_height': settings.card_size.height,
            'page_width': settings.page_format.width,
            'page_height': settings.page_format.height,
            'x_offset': x_offset,
            'y_offset': y_offset,
            'front_previews': front_previews,
            'back_previews': back_previews
        }), 200

    except Exception as e:
        logger.error(f"Ошибка превью: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Очистка временных файлов"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if session_id:
            session_dir = UPLOAD_FOLDER / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Очищена сессия: {session_id}")

            output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
            if output_file.exists():
                output_file.unlink()

            # Удаляем из хранилища прогресса
            if session_id in progress_store:
                del progress_store[session_id]

        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Ошибка очистки: {e}")
        return jsonify({'error': str(e)}), 500

def cleanup_old_sessions():
    """Периодическая очистка старых сессий"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=1)

        # Очистка uploads
        for session_dir in UPLOAD_FOLDER.iterdir():
            if session_dir.is_dir():
                dir_time = datetime.fromtimestamp(session_dir.stat().st_mtime)
                if dir_time < cutoff_time:
                    shutil.rmtree(session_dir, ignore_errors=True)
                    logger.info(f"Автоочистка сессии: {session_dir.name}")

        # Очистка output
        for output_file in OUTPUT_FOLDER.iterdir():
            if output_file.is_file():
                file_time = datetime.fromtimestamp(output_file.stat().st_mtime)
                if file_time < cutoff_time:
                    output_file.unlink()

    except Exception as e:
        logger.error(f"Ошибка автоочистки: {e}")

# Запускаем автоочистку при старте
cleanup_old_sessions()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)