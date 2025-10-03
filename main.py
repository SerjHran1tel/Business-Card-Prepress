# -*- coding: utf-8 -*-
# main.py - FastAPI Application
import os
import tempfile
import shutil
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from core.config import AppConfig
from utils.logger import setup_logging
from api.endpoints import api_router

# Настройка логирования
setup_logging()

logger = logging.getLogger(__name__)

# Глобальная конфигурация
app_config = AppConfig()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting Business Card Maker API")

    # Создаем временные директории
    os.makedirs("temp/uploads", exist_ok=True)
    os.makedirs("temp/converted", exist_ok=True)
    os.makedirs("temp/output", exist_ok=True)

    yield

    # Shutdown
    logger.info("Shutting down Business Card Maker API")

    # Очистка временных файлов
    try:
        shutil.rmtree("temp/uploads")
        shutil.rmtree("temp/converted")
        shutil.rmtree("temp/output")
    except Exception as e:
        logger.warning(f"Error cleaning temp directories: {e}")


app = FastAPI(
    title="Business Card Maker",
    description="Веб-приложение для подготовки визиток к печати",
    version="2.0.0",
    lifespan=lifespan
)

# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Подключение API роутов
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": "Business Card Maker",
        "version": "2.0.0"
    })


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return JSONResponse({
        "status": "healthy",
        "version": "2.0.0",
        "temp_dirs": {
            "uploads": os.path.exists("temp/uploads"),
            "converted": os.path.exists("temp/converted"),
            "output": os.path.exists("temp/output")
        }
    })


# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )