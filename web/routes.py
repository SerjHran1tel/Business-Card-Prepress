"""
Flask routes для web-интерфейса
"""
import logging
from datetime import datetime

from flask import render_template, request, send_file, jsonify

from config import UPLOAD_FOLDER, OUTPUT_FOLDER
from core import PageFormat, CardSize
from web.utils import (
    create_session_directories, save_uploaded_files,
    cleanup_session, progress_store, update_progress,
    image_to_base64
)
from web.background_tasks import start_background_processing

logger = logging.getLogger(__name__)


def configure_routes(app):
    """Настройка маршрутов Flask"""

    @app.route('/')
    def index():
        """Главная страница"""
        return render_template('index.html')

    @app.route('/upload', methods=['POST'])
    def upload_files():
        """Загрузка файлов"""
        try:
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            session_dir, front_dir, back_dir = create_session_directories(session_id)

            front_files = request.files.getlist('front_files')
            back_files = request.files.getlist('back_files')

            if not front_files or front_files[0].filename == '':
                return jsonify({'error': 'Не загружены файлы лицевой стороны'}), 400

            # Сохранение лицевых сторон
            front_file_info = save_uploaded_files(front_files, front_dir)

            # Сохранение оборотных сторон
            back_file_info = []
            if back_files and back_files[0].filename != '':
                back_file_info = save_uploaded_files(back_files, back_dir)

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
            start_background_processing(
                session_id,
                session_dir / 'front',
                session_dir / 'back',
                data,
                data.get('quantities', {})
            )

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

            # Импорты внутри функции
            from core.models import PrintSettings, PageFormat, CardSize
            from core.layout_calculator import LayoutCalculator
            from core.file_manager import FileManager

            settings = PrintSettings(
                page_format=PageFormat('A4', 210, 297),
                card_size=CardSize(90, 50)
            )

            # Применяем параметры из запроса
            _apply_preview_settings(settings, data)

            # Рассчитываем раскладку
            preview_data = LayoutCalculator.get_preview_data(settings)

            # Добавляем превью файлов
            session_id = data.get('session_id')
            _add_file_previews(preview_data, session_id)

            logger.info(f"Сгенерирован превью для сессии {session_id}")
            return jsonify(preview_data), 200

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
                cleanup_session(session_id)

            return jsonify({'success': True}), 200
        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")
            return jsonify({'error': str(e)}), 500


def _apply_preview_settings(settings, data):
    """Применение настроек для предпросмотра"""
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


def _add_file_previews(preview_data, session_id):
    """Добавление превью файлов"""
    from core.file_manager import FileManager

    preview_data['front_previews'] = []
    preview_data['back_previews'] = []

    if session_id:
        session_dir = UPLOAD_FOLDER / session_id
        front_dir = session_dir / 'front'
        back_dir = session_dir / 'back'

        if front_dir.exists():
            front_files = FileManager.scan_directory(front_dir)
            for file in front_files[:12]:
                preview = image_to_base64(file)
                preview_data['front_previews'].append({
                    'name': file.name,
                    'preview': preview
                })

        if back_dir.exists():
            back_files = FileManager.scan_directory(back_dir)
            for file in back_files[:12]:
                preview = image_to_base64(file)
                preview_data['back_previews'].append({
                    'name': file.name,
                    'preview': preview
                })