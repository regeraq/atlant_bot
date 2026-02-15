#!/bin/bash
# Скрипт для выполнения НА СЕРВЕРЕ
# Скопируйте этот файл на сервер и выполните: bash server_setup.sh

set -e

echo "🚀 Начинаем настройку и деплой бота..."

PROJECT_DIR="atlant_bot"
GIT_REPO="https://github.com/regeraq/atlant_bot.git"

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt-get update -qq

# Устанавливаем необходимые пакеты
echo "📦 Устанавливаем необходимые пакеты..."
sudo apt-get install -y git curl python3 python3-pip python3-venv docker.io docker-compose

# Добавляем пользователя в группу docker
echo "👤 Настраиваем права Docker..."
sudo usermod -aG docker $USER || true
newgrp docker || true

# Переходим в домашнюю директорию
cd ~

# Клонируем или обновляем репозиторий
if [ -d "$PROJECT_DIR" ]; then
    echo "📥 Обновляем существующий репозиторий..."
    cd $PROJECT_DIR
    git fetch origin
    git reset --hard origin/main 2>/dev/null || git reset --hard origin/master 2>/dev/null || true
    git pull
else
    echo "📥 Клонируем репозиторий..."
    git clone $GIT_REPO $PROJECT_DIR
    cd $PROJECT_DIR
fi

# Создаем необходимые директории
echo "📁 Создаем директории..."
mkdir -p data logs

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл из примера..."
    cp env.example .env
    echo ""
    echo "⚠️  ⚠️  ⚠️  ВАЖНО! ⚠️  ⚠️  ⚠️"
    echo "Отредактируйте файл .env и заполните:"
    echo "   - BOT_TOKEN (токен от @BotFather)"
    echo "   - ADMIN_IDS (ваш Telegram ID)"
    echo "   - FIRST_ADMIN_ID (ваш Telegram ID)"
    echo ""
    echo "Выполните: nano .env"
    echo ""
    read -p "Нажмите Enter после редактирования .env файла..."
fi

# Устанавливаем права на скрипты
chmod +x deploy.sh start.sh 2>/dev/null || true

# Запускаем деплой через Docker
echo "🐳 Запускаем Docker контейнер..."
if command -v docker-compose &> /dev/null; then
    docker-compose down || true
    echo "🔨 Собираем образ..."
    docker-compose build --no-cache
    echo "▶️  Запускаем контейнер..."
    docker-compose up -d
    echo ""
    echo "✅ Бот запущен через Docker!"
    echo ""
    echo "📋 Полезные команды:"
    echo "   Просмотр логов: docker-compose logs -f"
    echo "   Статус: docker-compose ps"
    echo "   Остановить: docker-compose stop"
    echo "   Запустить: docker-compose start"
    echo "   Перезапустить: docker-compose restart"
else
    echo "⚠️  Docker Compose не найден, используем обычный запуск..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Зависимости установлены"
    echo "⚠️  Запустите бота вручную: python bot/main.py"
fi

echo ""
echo "✅ Деплой завершен!"
echo ""

