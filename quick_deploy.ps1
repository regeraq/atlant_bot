# PowerShell скрипт для быстрого деплоя на сервер
# Использование: .\quick_deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 Начинаем автоматический деплой бота на сервер..." -ForegroundColor Green

# Параметры сервера
$SERVER_HOST = "185.217.197.220"
$SERVER_USER = "o-lvov"
$SERVER_PASS = "oi8HNGpNr3yP"
$GIT_REPO = "https://github.com/regeraq/atlant_bot.git"
$PROJECT_DIR = "atlant_bot"

Write-Host "`n📋 Информация о сервере:" -ForegroundColor Yellow
Write-Host "  Host: $SERVER_HOST"
Write-Host "  User: $SERVER_USER"
Write-Host "  Project: $PROJECT_DIR"
Write-Host ""

# Проверяем наличие plink (PuTTY) или используем ssh
$sshCommand = "ssh"
if (Get-Command plink -ErrorAction SilentlyContinue) {
    $sshCommand = "plink"
}

# Создаем скрипт для выполнения на сервере
$remoteScript = @"
#!/bin/bash
set -e

PROJECT_DIR="$PROJECT_DIR"
GIT_REPO="$GIT_REPO"

echo "🔧 Начинаем деплой на сервере..."

cd ~

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt-get update -qq

# Устанавливаем необходимые пакеты
echo "📦 Устанавливаем необходимые пакеты..."
sudo apt-get install -y git curl python3 python3-pip python3-venv docker.io docker-compose

# Добавляем пользователя в группу docker
sudo usermod -aG docker `$USER || true

# Клонируем или обновляем репозиторий
if [ -d "`$PROJECT_DIR" ]; then
    echo "📥 Обновляем существующий репозиторий..."
    cd `$PROJECT_DIR
    git fetch origin
    git reset --hard origin/main || git reset --hard origin/master
    git pull
else
    echo "📥 Клонируем репозиторий..."
    git clone `$GIT_REPO `$PROJECT_DIR
    cd `$PROJECT_DIR
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
fi

echo ""
echo "✅ Деплой завершен!"
"@

# Сохраняем скрипт во временный файл
$tempScript = [System.IO.Path]::GetTempFileName()
$remoteScript | Out-File -FilePath $tempScript -Encoding UTF8

Write-Host "📤 Загружаем скрипт деплоя на сервер..." -ForegroundColor Green

# Используем sshpass или другой метод для автоматического ввода пароля
# Для Windows можно использовать plink или настроить SSH ключи

Write-Host "`n⚠️  Для автоматического деплоя нужно:" -ForegroundColor Yellow
Write-Host "1. Установить SSH ключи для автоматического входа" -ForegroundColor Cyan
Write-Host "2. Или использовать plink (PuTTY)" -ForegroundColor Cyan
Write-Host "`n📋 Или выполните вручную на сервере:" -ForegroundColor Yellow
Write-Host "`nssh $SERVER_USER@$SERVER_HOST" -ForegroundColor Cyan
Write-Host "# Затем выполните команды из server_deploy_manual.md" -ForegroundColor Cyan

Write-Host "`n✅ Скрипт деплоя готов!" -ForegroundColor Green
Write-Host "📄 См. server_deploy_manual.md для подробных инструкций" -ForegroundColor Cyan

