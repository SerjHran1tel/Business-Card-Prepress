"""
Фоновые задачи обработки
"""
import logging
from threading import Thread

from web.utils import update_progress

logger = logging.getLogger(__name__)


def background_processing(session_id, front_dir, back_dir, settings_data, quantities):
    """Фоновая обработка файлов"""
    try:
        update_progress(session_id, "initializing", 5, "Инициализация обработки...")

        # Импорты внутри функции чтобы избежать циклических импортов
        from core.file_manager import FileManager
        from core.models import CardQuantity
        from core.imposition_app import ImpositionApp

        imposition = ImpositionApp()
        _configure_imposition_app(imposition, settings_data)

        update_progress(session_id, "validating", 30, "Проверка файлов...")
        validation = _validate_files(imposition, front_dir, back_dir)

        if not validation.is_valid:
            _handle_validation_error(session_id, validation)
            return

        update_progress(session_id, "preparing", 50, "Подготовка файлов...")
        front_cards, back_cards = _prepare_file_lists(imposition, front_dir, back_dir, quantities)

        update_progress(session_id, "generating", 70, "Создание PDF...")
        success = _generate_pdf(imposition, session_id, front_cards, back_cards)

        if success:
            _handle_success(session_id, validation)
        else:
            _handle_generation_error(session_id)

    except Exception as e:
        logger.error(f"Ошибка фоновой обработки: {e}")
        _handle_processing_error(session_id, str(e))


def _configure_imposition_app(imposition, settings_data):
    """Настройка приложения импозиции"""
    from core.models import PageFormat, CardSize, MatchingMode, ColorMode

    page_format_name = settings_data.get('page_format', 'A4')
    card_size_name = settings_data.get('card_size', 'Standard RU')

    # Настройка формата страницы
    if page_format_name == 'custom':
        imposition.settings.page_format = PageFormat(
            'Custom',
            float(settings_data.get('custom_page_width', 210)),
            float(settings_data.get('custom_page_height', 297))
        )
    else:
        page_formats = PageFormat.get_standard_formats()
        imposition.settings.page_format = page_formats.get(page_format_name, page_formats['A4'])

    # Настройка размера визитки
    if card_size_name == 'custom':
        imposition.settings.card_size = CardSize(
            float(settings_data.get('custom_card_width', 90)),
            float(settings_data.get('custom_card_height', 50))
        )
    else:
        card_sizes = CardSize.get_standard_sizes()
        imposition.settings.card_size = card_sizes.get(card_size_name, card_sizes['Standard RU'])

    # Дополнительные настройки
    imposition.settings.margin_top = float(settings_data.get('margin_top', 10))
    imposition.settings.margin_bottom = float(settings_data.get('margin_bottom', 10))
    imposition.settings.margin_left = float(settings_data.get('margin_left', 10))
    imposition.settings.margin_right = float(settings_data.get('margin_right', 10))
    imposition.settings.bleed = float(settings_data.get('bleed', 3))
    imposition.settings.gap = float(settings_data.get('gap', 2))
    imposition.settings.crop_marks = settings_data.get('crop_marks', True)
    imposition.settings.matching_mode = MatchingMode(settings_data.get('matching_mode', 'one_to_one'))
    imposition.settings.strict_name_matching = settings_data.get('strict_matching', True)
    imposition.settings.dpi = int(settings_data.get('dpi', 300))
    imposition.settings.output_dpi = int(settings_data.get('output_dpi', 300))
    imposition.settings.color_mode = ColorMode(settings_data.get('color_mode', 'rgb'))


def _validate_files(imposition, front_dir, back_dir):
    """Валидация файлов"""
    from core.file_manager import FileManager
    return FileManager.validate_files(
        front_dir, back_dir,
        imposition.settings.matching_mode,
        imposition.settings.strict_name_matching
    )


def _prepare_file_lists(imposition, front_dir, back_dir, quantities):
    """Подготовка списков файлов"""
    from core.file_manager import FileManager
    from core.models import CardQuantity

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
            matching_mode = imposition.settings.matching_mode.value

            if matching_mode == 'one_to_many':
                total_front = sum(c.quantity for c in front_cards)
                back_cards.append(CardQuantity(back_files[0], total_front))
            else:
                matches = FileManager.match_files(
                    front_files, back_files,
                    imposition.settings.strict_name_matching
                )
                for front_file in front_files:
                    back_file = matches.get(front_file)
                    if back_file:
                        qty = quantities.get('front', {}).get(front_file.name, 1)
                        back_cards.append(CardQuantity(back_file, qty))

    return front_cards, back_cards


def _generate_pdf(imposition, session_id, front_cards, back_cards):
    """Генерация PDF"""
    from config import OUTPUT_FOLDER
    output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
    return imposition.process(front_cards, back_cards, str(output_file))


def _handle_validation_error(session_id, validation):
    """Обработка ошибок валидации"""
    from web.utils import progress_store
    progress_store[session_id].update({
        'error': validation.get_report(),
        'success': False
    })


def _handle_success(session_id, validation):
    """Обработка успешного завершения"""
    from web.utils import progress_store, update_progress
    update_progress(session_id, "complete", 100, "Готово!")
    progress_store[session_id].update({
        'download_url': f'/download/{session_id}_imposition.pdf',
        'validation_report': validation.get_report(),
        'success': True
    })


def _handle_generation_error(session_id):
    """Обработка ошибки генерации"""
    from web.utils import progress_store
    progress_store[session_id].update({
        'error': 'Ошибка при создании PDF',
        'success': False
    })


def _handle_processing_error(session_id, error_message):
    """Обработка общей ошибки обработки"""
    from web.utils import progress_store
    progress_store[session_id].update({
        'error': error_message,
        'success': False
    })


def start_background_processing(session_id, front_dir, back_dir, settings_data, quantities):
    """Запуск фоновой обработки"""
    thread = Thread(
        target=background_processing,
        args=(session_id, front_dir, back_dir, settings_data, quantities)
    )
    thread.daemon = True
    thread.start()