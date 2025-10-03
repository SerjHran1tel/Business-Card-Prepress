"""
Flask Web Interface для Business Card Imposition System
"""

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import shutil
from pathlib import Path
from datetime import datetime
import base64
from io import BytesIO

# Импорт основного приложения
import sys

sys.path.append(os.path.dirname(__file__))
from imposition import (
    ImpositionApp, PageFormat, CardSize, MatchingMode,
    PrintSettings, FileManager, CardQuantity
)
from PIL import Image

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Директории
UPLOAD_FOLDER = Path('/app/uploads')
OUTPUT_FOLDER = Path('/app/output')
UPLOAD_FOLDER.mkdir(exist_ok=True, parents=True)
OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif', 'eps'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def image_to_base64(image_path: Path, max_size=(200, 200)) -> str | None:
    """Конвертирует изображение в base64 для превью"""
    try:
        if image_path.suffix.lower() == '.pdf':
            # Для PDF возвращаем заглушку
            return None

        img = Image.open(image_path)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except:
        return None


@app.route('/')
def index():
    """Главная страница"""
    page_formats = PageFormat.get_standard_formats()
    card_sizes = CardSize.get_standard_sizes()
    return render_template('index.html',
                           page_formats=page_formats,
                           card_sizes=card_sizes)


@app.route('/upload', methods=['POST'])
def upload_files():
    """Загрузка файлов"""
    try:
        # Создаем уникальную директорию для сессии
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        session_dir = UPLOAD_FOLDER / session_id
        front_dir = session_dir / 'front'
        back_dir = session_dir / 'back'

        front_dir.mkdir(parents=True, exist_ok=True)
        back_dir.mkdir(parents=True, exist_ok=True)

        # Получаем файлы
        front_files = request.files.getlist('front_files')
        back_files = request.files.getlist('back_files')

        if not front_files or front_files[0].filename == '':
            return jsonify({'error': 'Не загружены файлы лицевой стороны'}), 400

        # Сохраняем лицевые стороны
        front_file_info = []
        for file in front_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = front_dir / filename
                file.save(file_path)

                # Генерируем превью
                preview = image_to_base64(file_path)
                front_file_info.append({
                    'name': filename,
                    'preview': preview
                })

        # Сохраняем оборотные стороны
        back_file_info = []
        if back_files and back_files[0].filename != '':
            for file in back_files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = back_dir / filename
                    file.save(file_path)

                    # Генерируем превью
                    preview = image_to_base64(file_path)
                    back_file_info.append({
                        'name': filename,
                        'preview': preview
                    })

        return jsonify({
            'session_id': session_id,
            'front_files': front_file_info,
            'back_files': back_file_info
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/process', methods=['POST'])
def process_imposition():
    """Обработка и создание раскладки"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Не указан session_id'}), 400

        session_dir = UPLOAD_FOLDER / session_id
        if not session_dir.exists():
            return jsonify({'error': 'Сессия не найдена'}), 404

        # Создаем приложение
        imposition = ImpositionApp()

        # Настраиваем параметры из формы
        page_format_name = data.get('page_format', 'A4')
        card_size_name = data.get('card_size', 'Standard RU')
        matching_mode = data.get('matching_mode', 'one_to_one')
        strict_matching = data.get('strict_matching', True)

        # Применяем форматы
        page_formats = PageFormat.get_standard_formats()
        if page_format_name == 'custom':
            imposition.settings.page_format = PageFormat(
                'Custom',
                float(data.get('custom_page_width', 210)),
                float(data.get('custom_page_height', 297))
            )
        else:
            imposition.settings.page_format = page_formats.get(page_format_name,
                                                               page_formats['A4'])

        card_sizes = CardSize.get_standard_sizes()
        if card_size_name == 'custom':
            imposition.settings.card_size = CardSize(
                float(data.get('custom_card_width', 90)),
                float(data.get('custom_card_height', 50))
            )
        else:
            imposition.settings.card_size = card_sizes.get(card_size_name,
                                                           card_sizes['Standard RU'])

        # Настройки полей и вылетов
        imposition.settings.margin_top = float(data.get('margin_top', 10))
        imposition.settings.margin_bottom = float(data.get('margin_bottom', 10))
        imposition.settings.margin_left = float(data.get('margin_left', 10))
        imposition.settings.margin_right = float(data.get('margin_right', 10))
        imposition.settings.bleed = float(data.get('bleed', 3))
        imposition.settings.gap = float(data.get('gap', 2))
        imposition.settings.crop_marks = data.get('crop_marks', True)
        imposition.settings.matching_mode = MatchingMode(matching_mode)
        imposition.settings.strict_name_matching = strict_matching

        # Пути к файлам
        front_dir = session_dir / 'front'
        back_dir = session_dir / 'back'

        # Валидация файлов
        validation = FileManager.validate_files(
            front_dir, back_dir, imposition.settings.matching_mode, strict_matching
        )

        if not validation.is_valid:
            return jsonify({
                'error': 'Ошибка валидации',
                'details': validation.get_report()
            }), 400

        # Получаем количество копий для каждого файла
        quantities = data.get('quantities', {})

        # Формируем список лицевых карточек с количеством
        front_files = FileManager.scan_directory(front_dir)
        front_cards = []
        for file in front_files:
            qty = quantities.get('front', {}).get(file.name, 1)
            front_cards.append(CardQuantity(file, qty))

        # Формируем список оборотных карточек
        back_cards = None
        if back_dir.exists():
            back_files = FileManager.scan_directory(back_dir)
            if back_files:
                back_cards = []
                if matching_mode == 'one_to_many':
                    # Для режима один ко многим берем первый файл
                    total_front = sum(c.quantity for c in front_cards)
                    back_cards.append(CardQuantity(back_files[0], total_front))
                else:
                    # Для других режимов сопоставляем файлы
                    matches = FileManager.match_files(front_files, back_files, strict_matching)
                    for front_file in front_files:
                        back_file = matches.get(front_file)
                        if back_file:
                            qty = quantities.get('front', {}).get(front_file.name, 1)
                            back_cards.append(CardQuantity(back_file, qty))

        # Генерация PDF
        output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
        success = imposition.process(front_cards, back_cards, str(output_file))

        if success:
            return jsonify({
                'success': True,
                'download_url': f'/download/{session_id}_imposition.pdf',
                'validation_report': validation.get_report()
            }), 200
        else:
            return jsonify({'error': 'Ошибка при создании PDF'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание готового файла"""
    file_path = OUTPUT_FOLDER / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'Файл не найден'}), 404


@app.route('/preview', methods=['POST'])
def preview():
    """Предварительный просмотр раскладки"""
    try:
        data = request.json
        session_id = data.get('session_id')

        # Создаем настройки для расчета
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

        # Рассчитываем раскладку
        from imposition import LayoutCalculator
        cols, rows, x_offset, y_offset = LayoutCalculator.calculate_layout(settings)

        # Получаем превью файлов если есть session_id
        front_previews = []
        back_previews = []

        if session_id:
            session_dir = UPLOAD_FOLDER / session_id
            front_dir = session_dir / 'front'
            back_dir = session_dir / 'back'

            if front_dir.exists():
                front_files = FileManager.scan_directory(front_dir)
                for file in front_files[:12]:  # Максимум 12 превью
                    preview = image_to_base64(file)
                    front_previews.append({
                        'name': file.name,
                        'preview': preview
                    })

            if back_dir.exists():
                back_files = FileManager.scan_directory(back_dir)
                for file in back_files[:12]:  # Максимум 12 превью
                    preview = image_to_base64(file)
                    back_previews.append({
                        'name': file.name,
                        'preview': preview
                    })

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
        import traceback
        traceback.print_exc()
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

            output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
            if output_file.exists():
                output_file.unlink()

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)