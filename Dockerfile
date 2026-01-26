# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (если нужны)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Создаем директорию для базы данных
RUN mkdir -p /app/data

# Устанавливаем переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/bot_database.db

# Запускаем бота
CMD ["python", "bot/main.py"]

