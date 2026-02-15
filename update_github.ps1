# 🚀 Автоматическое обновление проекта на GitHub (PowerShell)
# Использование: .\update_github.ps1 [путь_к_проекту] [сообщение_коммита]

param(
    [string]$ProjectPath = "",
    [string]$CommitMessage = ""
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

# Определяем путь к проекту
if ([string]::IsNullOrEmpty($ProjectPath)) {
    $ProjectPath = Get-Location
} else {
    $ProjectPath = Resolve-Path $ProjectPath -ErrorAction SilentlyContinue
    if (-not $ProjectPath) {
        Print-Error "Директория не найдена: $ProjectPath"
        exit 1
    }
}

# Проверяем существование директории
if (-not (Test-Path $ProjectPath)) {
    Print-Error "Директория не найдена: $ProjectPath"
    exit 1
}

# Переходим в директорию проекта
Set-Location $ProjectPath

# Проверяем, что это git репозиторий
if (-not (Test-Path ".git")) {
    Print-Error "Это не git репозиторий!"
    exit 1
}

Print-Success "Найден проект: $ProjectPath"

# Получаем сообщение коммита
if ([string]::IsNullOrEmpty($CommitMessage)) {
    $CommitMessage = "Обновление проекта: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

Print-Warning "Сообщение коммита: $CommitMessage"

# Проверяем статус репозитория
Write-Host ""
Print-Warning "Проверка изменений..."
git status --short

# Проверяем, есть ли изменения
$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Print-Warning "Нет изменений для коммита"
    exit 0
}

# Добавляем все изменения
Write-Host ""
Print-Warning "Добавление всех изменений..."
git add .

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при добавлении файлов"
    exit 1
}

Print-Success "Файлы добавлены"

# Создаем коммит
Write-Host ""
Print-Warning "Создание коммита..."
git commit -m $CommitMessage

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при создании коммита"
    exit 1
}

Print-Success "Коммит создан"

# Получаем имя текущей ветки
$CurrentBranch = git branch --show-current
Print-Warning "Текущая ветка: $CurrentBranch"

# Пушим изменения
Write-Host ""
Print-Warning "Отправка изменений на GitHub..."
git push origin $CurrentBranch

if ($LASTEXITCODE -ne 0) {
    Print-Error "Ошибка при отправке на GitHub"
    Print-Warning "Возможно, нужно настроить удаленный репозиторий:"
    Print-Warning "git remote add origin https://github.com/username/repo.git"
    exit 1
}

Print-Success "Изменения успешно отправлены на GitHub!"
Write-Host ""
Print-Success "Проект обновлен: $ProjectPath"
Print-Success "Ветка: $CurrentBranch"
Print-Success "Коммит: $CommitMessage"

