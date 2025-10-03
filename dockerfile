FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск тестов, но продолжение сборки даже при неудаче
RUN python -m unittest discover tests || true

CMD ["python", "main.py"]