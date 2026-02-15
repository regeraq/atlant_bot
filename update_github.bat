@echo off
REM 🚀 Автоматическое обновление проекта на GitHub (Windows Batch)
REM Использование: update_github.bat [путь_к_проекту] [сообщение_коммита]

setlocal enabledelayedexpansion

REM Определяем путь к проекту
if "%~1"=="" (
    set "PROJECT_PATH=%CD%"
) else (
    set "PROJECT_PATH=%~1"
)

REM Проверяем существование директории
if not exist "%PROJECT_PATH%" (
    echo ❌ Директория не найдена: %PROJECT_PATH%
    exit /b 1
)

REM Переходим в директорию проекта
cd /d "%PROJECT_PATH%"

REM Проверяем, что это git репозиторий
if not exist ".git" (
    echo ❌ Это не git репозиторий!
    exit /b 1
)

echo ✅ Найден проект: %PROJECT_PATH%

REM Получаем сообщение коммита
if "%~2"=="" (
    for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set mydate=%%c-%%b-%%a
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do set mytime=%%a:%%b
    set "COMMIT_MESSAGE=Обновление проекта: %mydate% %mytime%"
) else (
    set "COMMIT_MESSAGE=%~2"
)

echo ⚠️  Сообщение коммита: %COMMIT_MESSAGE%

REM Проверяем статус репозитория
echo.
echo ⚠️  Проверка изменений...
git status --short

REM Проверяем, есть ли изменения
git status --porcelain >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Нет изменений для коммита
    exit /b 0
)

REM Добавляем все изменения
echo.
echo ⚠️  Добавление всех изменений...
git add .
if errorlevel 1 (
    echo ❌ Ошибка при добавлении файлов
    exit /b 1
)

echo ✅ Файлы добавлены

REM Создаем коммит
echo.
echo ⚠️  Создание коммита...
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 (
    echo ❌ Ошибка при создании коммита
    exit /b 1
)

echo ✅ Коммит создан

REM Получаем имя текущей ветки
for /f "delims=" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo ⚠️  Текущая ветка: !CURRENT_BRANCH!

REM Пушим изменения
echo.
echo ⚠️  Отправка изменений на GitHub...
git push origin !CURRENT_BRANCH!
if errorlevel 1 (
    echo ❌ Ошибка при отправке на GitHub
    echo ⚠️  Возможно, нужно настроить удаленный репозиторий:
    echo ⚠️  git remote add origin https://github.com/username/repo.git
    exit /b 1
)

echo ✅ Изменения успешно отправлены на GitHub!
echo.
echo ✅ Проект обновлен: %PROJECT_PATH%
echo ✅ Ветка: !CURRENT_BRANCH!
echo ✅ Коммит: %COMMIT_MESSAGE%

endlocal

