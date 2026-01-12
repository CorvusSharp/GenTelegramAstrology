# Astro Bot 🌌

Бот для генерации астрологических отчетов (Синастрия) с использованием OpenAI GPT-4o, генерации PDF (ReportLab) и DOCX (python-docx).

## 📋 Требования

- Python 3.10+
- OpenAI API Key
- Telegram Bot Token

## ⚙️ Установка и запуск (Linux / Ubuntu VPS)

Это рекомендуемый способ для постоянной работы бота на сервере.

### 1. Подготовка сервера

Обновите пакеты и установите Python/Git:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-venv python3-pip git -y
```

### 2. Клонирование репозитория

```bash
cd /opt
sudo git clone https://github.com/CorvusSharp/GenTelegramAstrology.git astrolog_bot
# Или ваша ссылка на репозиторий
sudo chown -R $USER:$USER /opt/astrolog_bot
cd /opt/astrolog_bot
```

### 3. Настройка окружения (venv)

```bash
# Создаем виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate

# Обновляем pip и ставим зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Конфигурация (.env)

Создайте файл с настройками:
```bash
cp env_example .env
nano .env
```
Вставьте ваши ключи:
```ini
TELEGRAM_BOT_TOKEN=ваш_токен_от_botfather
OPENAI_API_KEY=ваш_ключ_openai
```

### 5. Пробный запуск

Запустите бота вручную, чтобы убедиться, что ошибок нет:
```bash
python astro_bot/main.py
```
*Нажмите `Ctrl+C`, чтобы остановить.*

---

## 🚀 Запуск как Systemd сервис (Автозапуск)

Чтобы бот работал в фоне и перезапускался автоматически при падении или перезагрузке сервера.

### 1. Создание unit-файла

Создайте файл службы:
```bash
sudo nano /etc/systemd/system/astro_bot.service
```

Вставьте следующий текст (замените `root` на вашего пользователя, если нужно, но для `/opt` часто используют root или специального юзера):

```ini
[Unit]
Description=Telegram Astrology Bot
After=network.target

[Service]
# Имя пользователя, от которого запускается бот
User=root
# Рабочая директория
WorkingDirectory=/opt/astrolog_bot
# Команда запуска (путь к python внутри venv)
ExecStart=/opt/astrolog_bot/venv/bin/python astro_bot/main.py

# Перезапуск при падении
Restart=always
RestartSec=5

# Логирование
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=astro_bot

[Install]
WantedBy=multi-user.target
```

### 2. Активация службы

```bash
sudo systemctl daemon-reload
sudo systemctl enable astro_bot
sudo systemctl start astro_bot
```

### 3. Проверка статуса и логов

```bash
# Статус
sudo systemctl status astro_bot

# Чтение логов в реальном времени
sudo journalctl -u astro_bot -f
```

---

## 🐳 Запуск через Docker (Альтернатива)

Если вы предпочитаете Docker:

1. Настройте `.env` файл.
2. Запустите контейнеры:
```bash
docker-compose up -d --build
```

---

## 🔄 Обновление бота

Когда вы внесли изменения в код и хотите обновить сервер:

```bash
cd /opt/astrolog_bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # Если менялись зависимости
sudo systemctl restart astro_bot
```

## 📂 Структура проекта

- `astro_bot/` — Исходный код бота
  - `main.py` — Точка входа
  - `telegram_bot.py` — Логика Telegram
  - `prompts.py` — Текстовые промпты для LLM
  - `pdf_renderer.py` / `docx_renderer.py` — Генераторы файлов
- `fonts/` — Шрифты (Times New Roman) для PDF
- `requirements.txt` — Python зависимости
