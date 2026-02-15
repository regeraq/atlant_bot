# 🚀 Автоматическая настройка GitHub Pages для Telegram Mini App
# Этот скрипт подготовит и загрузит frontend на GitHub

param(
    [string]$GitHubUsername = "",
    [string]$RepositoryName = "atlant_bot"
)

# Функции для вывода сообщений
function Print-Success {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Print-Warning {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Print-Error {
    Write-Host "❌ $args" -ForegroundColor Red
}

function Print-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Cyan
}

# Проверяем, что мы в правильной директории
$ProjectPath = Get-Location
if (-not (Test-Path "$ProjectPath\frontend\index.html")) {
    Print-Error "Файл frontend/index.html не найден!"
    Print-Info "Убедитесь, что вы находитесь в корневой директории проекта"
    exit 1
}

Print-Success "Найден проект: $ProjectPath"

# Проверяем git
if (-not (Test-Path ".git")) {
    Print-Warning "Инициализация git репозитория..."
    git init
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Ошибка инициализации git"
        exit 1
    }
}

# Проверяем удаленный репозиторий
$remoteUrl = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Print-Warning "Удаленный репозиторий не настроен"
    
    if ([string]::IsNullOrEmpty($GitHubUsername)) {
        $GitHubUsername = Read-Host "Введите ваш GitHub username"
    }
    
    $remoteUrl = "https://github.com/$GitHubUsername/$RepositoryName.git"
    Print-Info "Добавление удаленного репозитория: $remoteUrl"
    git remote add origin $remoteUrl
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Ошибка добавления удаленного репозитория"
        Print-Info "Убедитесь, что репозиторий существует на GitHub"
        exit 1
    }
} else {
    Print-Success "Удаленный репозиторий: $remoteUrl"
    # Извлекаем username из URL
    if ($remoteUrl -match "github\.com/([^/]+)/") {
        $GitHubUsername = $matches[1]
        Print-Info "GitHub username: $GitHubUsername"
    }
}

# Проверяем, что frontend/index.html существует
if (-not (Test-Path "frontend\index.html")) {
    Print-Error "Файл frontend/index.html не найден!"
    exit 1
}

Print-Success "Файл frontend/index.html найден"

# Проверяем изменения
Print-Info "Проверка изменений..."
$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Print-Warning "Нет изменений для коммита"
} else {
    Write-Host $status
}

# Добавляем все файлы
Print-Info "Добавление файлов..."
git add .

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при добавлении файлов"
    exit 1
}

# Создаем коммит
$commitMessage = "Добавлен Telegram Mini App (Web App) для каталога автомобилей"
Print-Info "Создание коммита: $commitMessage"
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Print-Warning "Возможно, нет изменений для коммита или коммит уже существует"
}

# Получаем текущую ветку
$currentBranch = git branch --show-current
if ([string]::IsNullOrEmpty($currentBranch)) {
    $currentBranch = "main"
    Print-Info "Создание ветки main..."
    git checkout -b main
}

Print-Info "Текущая ветка: $currentBranch"

# Пушим изменения
Print-Info "Отправка изменений на GitHub..."
git push -u origin $currentBranch

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при отправке на GitHub"
    Print-Warning "Возможные причины:"
    Print-Warning "1. Репозиторий не существует на GitHub"
    Print-Warning "2. Нет прав доступа"
    Print-Warning "3. Нужна аутентификация"
    exit 1
}

Print-Success "Изменения успешно отправлены на GitHub!"

# Формируем URL для GitHub Pages
$pagesUrl = "https://$GitHubUsername.github.io/$RepositoryName/"
if ($RepositoryName -ne "atlant_bot") {
    $pagesUrl = "https://$GitHubUsername.github.io/$RepositoryName/"
}

Write-Host ""
Print-Success "=" * 60
Print-Success "Следующие шаги для настройки GitHub Pages:"
Print-Success "=" * 60
Write-Host ""
Print-Info "1. Откройте ваш репозиторий на GitHub:"
Write-Host "   https://github.com/$GitHubUsername/$RepositoryName" -ForegroundColor Cyan
Write-Host ""
Print-Info "2. Перейдите в Settings → Pages"
Write-Host ""
Print-Info "3. В разделе 'Source' выберите:"
Write-Host "   - Branch: $currentBranch" -ForegroundColor Yellow
Write-Host "   - Folder: / (root)" -ForegroundColor Yellow
Write-Host ""
Print-Info "4. Нажмите Save"
Write-Host ""
Print-Info "5. Подождите 1-2 минуты, пока GitHub Pages активируется"
Write-Host ""
Print-Info "6. Ваш Web App будет доступен по адресу:"
Write-Host "   $pagesUrl" -ForegroundColor Green
Write-Host ""
Print-Warning "ВАЖНО: После активации GitHub Pages обновите URL в коде бота:"
Write-Host "   Файл: bot/keyboards/user_keyboards.py" -ForegroundColor Yellow
Write-Host "   Замените URL на: $pagesUrl" -ForegroundColor Yellow
Write-Host ""
Print-Success "=" * 60

