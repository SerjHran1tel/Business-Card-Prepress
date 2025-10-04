"""
Вспомогательные функции для web-интерфейса
"""
import base64
import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from PIL import Image
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, OUTPUT_FOLDER

logger = logging.getLogger(__name__)

# Хранилище прогресса
progress_store = {}


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_uploaded_file(file) -> tuple[bool, str]:
    """Валидация загружаемого файла"""
    try:
        if not allowed_file(file.filename):
            return False, f"Неподдерживаемый формат файла: {file.filename}"

        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > 50 * 1024 * 1024:
            return False, f"Файл слишком большой: {file.filename} ({file_size/1024/1024:.1f}MB)"

        if file_size == 0:
            return False, f"Файл пустой: {file.filename}"

        return True, "OK"

    except Exception as e:
        return False, f"Ошибка валидации файла: {str(e)}"


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


def create_session_directories(session_id):
    """Создание директорий для сессии"""
    session_dir = UPLOAD_FOLDER / session_id
    front_dir = session_dir / 'front'
    back_dir = session_dir / 'back'

    front_dir.mkdir(parents=True, exist_ok=True)
    back_dir.mkdir(parents=True, exist_ok=True)

    return session_dir, front_dir, back_dir


def save_uploaded_files(files, directory):
    """Сохранение загруженных файлов"""
    from processing.image_processor import ImageProcessor

    file_info = []
    for file in files:
        if file and allowed_file(file.filename):
            is_valid, message = validate_uploaded_file(file)
            if not is_valid:
                raise ValueError(message)

            filename = secure_filename(file.filename)
            file_path = directory / filename
            file.save(file_path)

            preview = ImageProcessor.create_preview(file_path)
            file_info.append({
                'name': filename,
                'preview': preview
            })

    return file_info


def cleanup_session(session_id):
    """Очистка файлов сессии"""
    try:
        session_dir = UPLOAD_FOLDER / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
            logger.info(f"Очищена сессия: {session_id}")

        output_file = OUTPUT_FOLDER / f"{session_id}_imposition.pdf"
        if output_file.exists():
            output_file.unlink()

        if session_id in progress_store:
            del progress_store[session_id]

    except Exception as e:
        logger.error(f"Ошибка очистки сессии: {e}")


def cleanup_old_sessions():
    """Периодическая очистка старых сессий"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=1)

        for session_dir in UPLOAD_FOLDER.iterdir():
            if session_dir.is_dir():
                dir_time = datetime.fromtimestamp(session_dir.stat().st_mtime)
                if dir_time < cutoff_time:
                    import shutil
                    shutil.rmtree(session_dir, ignore_errors=True)
                    logger.info(f"Автоочистка сессии: {session_dir.name}")

        for output_file in OUTPUT_FOLDER.iterdir():
            if output_file.is_file():
                file_time = datetime.fromtimestamp(output_file.stat().st_mtime)
                if file_time < cutoff_time:
                    output_file.unlink()

    except Exception as e:
        logger.error(f"Ошибка автоочистки: {e}")


def image_to_base64(image_path: Path, max_size=(200, 200)) -> str | None:
    """Конвертирует изображение в base64 для превью"""
    try:
        if image_path.suffix.lower() == '.pdf':
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