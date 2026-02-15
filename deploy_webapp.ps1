# 🚀 Полная автоматизация развертывания Telegram Mini App на GitHub Pages
# Этот скрипт сделает все за вас: загрузит файлы, настроит GitHub Pages

param(
    [string]$GitHubUsername = "",
    [string]$RepositoryName = "atlant_bot",
    [switch]$SkipPagesSetup = $false
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

function Print-Step {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $args" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

# Проверяем, что мы в правильной директории
$ProjectPath = Get-Location
if (-not (Test-Path "$ProjectPath\frontend\index.html")) {
    Print-Error "Файл frontend/index.html не найден!"
    Print-Info "Убедитесь, что вы находитесь в корневой директории проекта"
    exit 1
}

Print-Step "ШАГ 1: Проверка окружения"

# Исправляем проблему с git ownership (если нужно)
Print-Info "Проверка настроек git..."
$safeDir = git config --global --get-all safe.directory | Select-String "F:/atlant_bot"
if (-not $safeDir) {
    Print-Info "Добавление директории в safe.directory..."
    git config --global --add safe.directory "F:/atlant_bot" 2>$null
}

# Проверяем git репозиторий
if (-not (Test-Path ".git")) {
    Print-Warning "Инициализация git репозитория..."
    git init
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Ошибка инициализации git"
        exit 1
    }
    Print-Success "Git репозиторий инициализирован"
}

# Проверяем удаленный репозиторий
Print-Step "ШАГ 2: Настройка удаленного репозитория"

$remoteUrl = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($remoteUrl)) {
    Print-Warning "Удаленный репозиторий не настроен"
    
    if ([string]::IsNullOrEmpty($GitHubUsername)) {
        $GitHubUsername = Read-Host "Введите ваш GitHub username (например: regeraq)"
    }
    
    $remoteUrl = "https://github.com/$GitHubUsername/$RepositoryName.git"
    Print-Info "Добавление удаленного репозитория: $remoteUrl"
    
    # Проверяем, не добавлен ли уже origin
    $existingRemote = git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) {
        Print-Info "Удаленный репозиторий уже существует, обновляем..."
        git remote set-url origin $remoteUrl
    } else {
        git remote add origin $remoteUrl
    }
    
    if ($LASTEXITCODE -ne 0) {
        Print-Error "Ошибка добавления удаленного репозитория"
        Print-Info "Убедитесь, что репозиторий существует на GitHub"
        Print-Info "Создайте репозиторий на https://github.com/new если его нет"
        exit 1
    }
    Print-Success "Удаленный репозиторий настроен"
} else {
    Print-Success "Удаленный репозиторий: $remoteUrl"
    # Извлекаем username из URL
    if ($remoteUrl -match "github\.com[/:]([^/]+)/") {
        $GitHubUsername = $matches[1]
        Print-Info "GitHub username: $GitHubUsername"
    }
}

# Проверяем файлы
Print-Step "ШАГ 3: Проверка файлов"

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
Print-Step "ШАГ 4: Добавление файлов в git"

Print-Info "Добавление всех файлов..."
git add .

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при добавлении файлов"
    exit 1
}
Print-Success "Файлы добавлены"

# Создаем коммит
Print-Step "ШАГ 5: Создание коммита"

$commitMessage = "🚀 Добавлен Telegram Mini App (Web App) для каталога автомобилей"
Print-Info "Создание коммита: $commitMessage"
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    $lastCommit = git log -1 --pretty=format:"%s" 2>$null
    if ($lastCommit -eq $commitMessage) {
        Print-Warning "Коммит уже существует, пропускаем..."
    } else {
        Print-Warning "Возможно, нет изменений для коммита"
    }
} else {
    Print-Success "Коммит создан"
}

# Получаем текущую ветку
$currentBranch = git branch --show-current
if ([string]::IsNullOrEmpty($currentBranch)) {
    $currentBranch = "main"
    Print-Info "Создание ветки main..."
    git checkout -b main 2>$null
    if ($LASTEXITCODE -ne 0) {
        git branch -M main
    }
}

Print-Info "Текущая ветка: $currentBranch"

# Пушим изменения
Print-Step "ШАГ 6: Отправка на GitHub"

Print-Info "Отправка изменений на GitHub..."
git push -u origin $currentBranch

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при отправке на GitHub"
    Print-Warning "Возможные причины:"
    Print-Warning "1. Репозиторий не существует на GitHub - создайте его на https://github.com/new"
    Print-Warning "2. Нет прав доступа"
    Print-Warning "3. Нужна аутентификация (используйте Personal Access Token)"
    Print-Warning ""
    Print-Info "Попробуйте выполнить вручную:"
    Write-Host "   git push -u origin $currentBranch" -ForegroundColor Yellow
    exit 1
}

Print-Success "Изменения успешно отправлены на GitHub!"

# Формируем URL для GitHub Pages
$pagesUrl = "https://$GitHubUsername.github.io/$RepositoryName/"

Write-Host ""
Print-Step "ШАГ 7: Настройка GitHub Pages"

if (-not $SkipPagesSetup) {
    Write-Host ""
    Print-Success "=" * 70
    Print-Success "📋 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ GITHUB PAGES:"
    Print-Success "=" * 70
    Write-Host ""
    Print-Info "1. Откройте ваш репозиторий на GitHub:"
    Write-Host "   https://github.com/$GitHubUsername/$RepositoryName" -ForegroundColor Cyan
    Write-Host ""
    Print-Info "2. Перейдите в Settings → Pages (в левом меню)"
    Write-Host ""
    Print-Info "3. В разделе 'Source' выберите:"
    Write-Host "   • Branch: $currentBranch" -ForegroundColor Yellow
    Write-Host "   • Folder: / (root)" -ForegroundColor Yellow
    Write-Host ""
    Print-Info "4. Нажмите Save"
    Write-Host ""
    Print-Info "5. Подождите 1-2 минуты, пока GitHub Pages активируется"
    Write-Host ""
    Print-Info "6. Проверьте доступность по адресу:"
    Write-Host "   $pagesUrl" -ForegroundColor Green
    Write-Host ""
    Print-Warning "⚠️  ВАЖНО: После активации GitHub Pages выполните:"
    Write-Host "   .\update_webapp_url.ps1 -WebAppUrl `"$pagesUrl`"" -ForegroundColor Yellow
    Write-Host ""
    Print-Success "=" * 70
} else {
    Print-Info "Пропущена настройка GitHub Pages (используйте -SkipPagesSetup)"
}

Write-Host ""
Print-Success "🎉 Развертывание завершено!"
Print-Info "Ваш Web App будет доступен по адресу: $pagesUrl"
Write-Host ""

