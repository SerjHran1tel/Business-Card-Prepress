# run.py
import uvicorn
import os

if __name__ == "__main__":
    # Создаем необходимые директории
    os.makedirs("temp/uploads", exist_ok=True)
    os.makedirs("temp/converted", exist_ok=True)
    os.makedirs("temp/output", exist_ok=True)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )