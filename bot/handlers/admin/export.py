"""
Обработчики экспорта данных для администраторов
"""
import os
import tempfile
import logging
from datetime import datetime
from aiogram.types import CallbackQuery
from aiogram.types import FSInputFile
from bot.database.database import export_database
from bot.utils.helpers import safe_callback_answer
from .common import admin_required

logger = logging.getLogger(__name__)


@admin_required
async def handle_admin_export_db_callback(callback: CallbackQuery):
    """Выгрузка базы данных"""
    db_data = await export_database()
    
    if not db_data:
        await callback.message.answer(
            """❌ <b>ОШИБКА ПРИ ВЫГРУЗКЕ БД</b>

💡 Не удалось прочитать базу данных.""",
            parse_mode='HTML'
        )
        await safe_callback_answer(callback, "❌ Ошибка при выгрузке БД", show_alert=True)
        return
    
    # Формируем имя файла с датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bot_database_backup_{timestamp}.db"
    
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            tmp_file.write(db_data)
            tmp_path = tmp_file.name
        
        # Отправляем файл
        document = FSInputFile(tmp_path, filename=filename)
        await callback.message.answer_document(
            document=document,
            caption=f"""💾 <b>Резервная копия базы данных</b>

━━━━━━━━━━━━━━━━━━━━━━
📅 <b>Создана:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
📦 <b>Размер:</b> {len(db_data) / 1024:.2f} КБ
━━━━━━━━━━━━━━━━━━━━━━""",
            parse_mode='HTML'
        )
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        await safe_callback_answer(callback, "✅ База данных успешно выгружена!")
        
    except Exception as e:
        await callback.message.answer(
            f"""❌ <b>ОШИБКА ПРИ ОТПРАВКЕ ФАЙЛА</b>

💡 Детали: {str(e)[:200]}""",
            parse_mode='HTML'
        )
        # Удаляем временный файл в случае ошибки
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass




