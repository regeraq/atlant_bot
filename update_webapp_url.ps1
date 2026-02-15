# 🔧 Обновление URL Web App в коде бота
# Использование: .\update_webapp_url.ps1 -WebAppUrl "https://username.github.io/repo/"

param(
    [Parameter(Mandatory=$true)]
    [string]$WebAppUrl
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

# Убеждаемся, что URL заканчивается на /
if (-not $WebAppUrl.EndsWith("/")) {
    $WebAppUrl = $WebAppUrl + "/"
}

Print-Info "Обновление URL Web App на: $WebAppUrl"

$keyboardFile = "bot\keyboards\user_keyboards.py"

if (-not (Test-Path $keyboardFile)) {
    Print-Error "Файл $keyboardFile не найден!"
    exit 1
}

# Читаем файл
$content = Get-Content $keyboardFile -Raw

# Обновляем URL в функции get_main_menu
$pattern1 = '(web_app_url\s*=\s*")[^"]+(")'
if ($content -match $pattern1) {
    $content = $content -replace $pattern1, "`$1$WebAppUrl`$2"
    Print-Success "URL обновлен в функции get_main_menu()"
} else {
    Print-Warning "URL не найден в функции get_main_menu()"
}

# Обновляем URL в функции get_webapp_keyboard
$pattern2 = '(web_app_url\s*=\s*")[^"]+(")'
# Используем более специфичный паттерн для get_webapp_keyboard
$pattern2 = '(def get_webapp_keyboard\(\):[\s\S]*?web_app_url\s*=\s*")[^"]+(")'
if ($content -match $pattern2) {
    $content = $content -replace $pattern2, "`$1$WebAppUrl`$2"
    Print-Success "URL обновлен в функции get_webapp_keyboard()"
} else {
    # Попробуем более простой паттерн
    $simplePattern = '("https://[^"]+github\.io/[^"]+/")'
    if ($content -match $simplePattern) {
        $content = $content -replace $simplePattern, "`"$WebAppUrl`""
        Print-Success "URL обновлен (простой паттерн)"
    } else {
        Print-Warning "URL не найден в функции get_webapp_keyboard()"
    }
}

# Записываем обновленный файл
Set-Content -Path $keyboardFile -Value $content -NoNewline

Print-Success "Файл $keyboardFile обновлен"
Print-Info "Теперь перезапустите бота, чтобы изменения вступили в силу"

