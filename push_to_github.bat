@echo off
chcp 65001 >nul
echo 🚀 Загрузка изменений на GitHub...
echo.

cd /d "F:\atlant_bot"

echo ✅ Добавление всех файлов...
git add .

echo ✅ Создание коммита...
git commit -m "Добавлен Telegram Mini App Web App для каталога автомобилей"

echo ✅ Отправка на GitHub...
git push origin main

echo.
echo ✅ Готово! Изменения отправлены на GitHub
echo.
echo 📋 Следующие шаги:
echo 1. Откройте https://github.com/regeraq/atlant_bot
echo 2. Перейдите в Settings ^> Pages
echo 3. Выберите Branch: main, Folder: / (root)
echo 4. Нажмите Save
echo 5. Ваш Web App будет доступен по адресу:
echo    https://regeraq.github.io/atlant_bot/
echo.
pause

