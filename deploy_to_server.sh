#!/bin/bash

# Скрипт автоматического деплоя бота на сервер
# Использование: ./deploy_to_server.sh

set -e  # Остановка при ошибке

echo "🚀 Начинаем автоматический деплой бота на сервер..."

# Параметры сервера
SERVER_HOST="185.217.197.220"
SERVER_USER="o-lvov"
SERVER_PASS="oi8HNGpNr3yP"
GIT_REPO="https://github.com/regeraq/atlant_bot.git"
PROJECT_DIR="atlant_bot"

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📋 Информация о сервере:${NC}"
echo "  Host: $SERVER_HOST"
echo "  User: $SERVER_USER"
echo "  Project: $PROJECT_DIR"
echo ""

# Проверяем наличие sshpass (для автоматического ввода пароля)
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass не установлен. Устанавливаем...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    else
        echo -e "${RED}❌ Не удалось установить sshpass автоматически${NC}"
        echo "Установите вручную: https://github.com/keimpx/sshpass"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Подключаемся к серверу...${NC}"

# Создаем скрипт для выполнения на сервере
cat > /tmp/deploy_remote.sh << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

PROJECT_DIR="atlant_bot"
GIT_REPO="https://github.com/regeraq/atlant_bot.git"

echo "🔧 Начинаем деплой на сервере..."

# Переходим в домашнюю директорию
cd ~

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt-get update -qq

# Устанавливаем необходимые пакеты
echo "📦 Устанавливаем необходимые пакеты..."
sudo apt-get install -y git curl python3 python3-pip python3-venv docker.io docker-compose

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER || true

# Клонируем или обновляем репозиторий
if [ -d "$PROJECT_DIR" ]; then
    echo "📥 Обновляем существующий репозиторий..."
    cd $PROJECT_DIR
    git fetch origin
    git reset --hard origin/main || git reset --hard origin/master
    git pull
else
    echo "📥 Клонируем репозиторий..."
    git clone $GIT_REPO $PROJECT_DIR
    cd $PROJECT_DIR
fi

# Создаем необходимые директории
mkdir -p data logs

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл из примера..."
    cp env.example .env
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте файл .env и заполните:"
    echo "   - BOT_TOKEN (токен от @BotFather)"
    echo "   - ADMIN_IDS (ваш Telegram ID)"
    echo "   - FIRST_ADMIN_ID (ваш Telegram ID)"
    echo ""
    echo "Выполните: nano .env"
fi

# Устанавливаем права на скрипты
chmod +x deploy.sh start.sh 2>/dev/null || true

# Запускаем деплой через Docker
echo "🐳 Запускаем Docker контейнер..."
if command -v docker-compose &> /dev/null; then
    docker-compose down || true
    docker-compose build --no-cache
    docker-compose up -d
    echo "✅ Бот запущен через Docker!"
    echo "📋 Просмотр логов: docker-compose logs -f"
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
echo "📋 Проверьте статус: docker-compose ps"
echo "📋 Логи: docker-compose logs -f"
REMOTE_SCRIPT

# Копируем скрипт на сервер и выполняем
echo -e "${GREEN}📤 Загружаем скрипт деплоя на сервер...${NC}"
sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no /tmp/deploy_remote.sh ${SERVER_USER}@${SERVER_HOST}:~/deploy_remote.sh

echo -e "${GREEN}▶️  Выполняем деплой на сервере...${NC}"
sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} "chmod +x ~/deploy_remote.sh && bash ~/deploy_remote.sh"

# Удаляем временный файл
rm /tmp/deploy_remote.sh

echo ""
echo -e "${GREEN}✅ Деплой завершен!${NC}"
echo ""
echo "📋 Следующие шаги:"
echo "1. Подключитесь к серверу: ssh ${SERVER_USER}@${SERVER_HOST}"
echo "2. Перейдите в директорию: cd atlant_bot"
echo "3. Отредактируйте .env файл: nano .env"
echo "4. Заполните BOT_TOKEN, ADMIN_IDS, FIRST_ADMIN_ID"
echo "5. Перезапустите бота: docker-compose restart"
echo ""
echo "📊 Проверка статуса:"
echo "   ssh ${SERVER_USER}@${SERVER_HOST} 'cd atlant_bot && docker-compose ps'"

