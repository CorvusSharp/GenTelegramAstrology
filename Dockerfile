FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
# build-essential нужен для компиляции некоторых python пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код проекта
COPY . .

# Команда для запуска бота
# Предполагается, что запуск идет из корня проекта, как локально
# PYTHONPATH автоматически включает текущую директорию (.)
CMD ["python", "astro_bot/telegram_bot.py"]
