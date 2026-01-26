"""
Unit тесты для модуля scheduler.py
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, date, timedelta
from bot.utils.scheduler import PaymentReminderScheduler


class TestPaymentReminderScheduler:
    """Тесты для класса PaymentReminderScheduler"""
    
    @pytest.fixture
    def mock_bot(self):
        """Создает мок бота"""
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def scheduler(self, mock_bot):
        """Создает экземпляр планировщика"""
        return PaymentReminderScheduler(mock_bot)
    
    @pytest.fixture
    def sample_rental_daily(self):
        """Тестовая аренда с ежедневным напоминанием"""
        return {
            'id': 1,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car',
            'daily_price': 5000,
            'reminder_time': '12:00',
            'reminder_type': 'daily',
            'start_date': datetime.now() - timedelta(days=5),
            'last_reminder_date': None
        }
    
    @pytest.fixture
    def sample_rental_weekly(self):
        """Тестовая аренда с еженедельным напоминанием"""
        return {
            'id': 2,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car',
            'daily_price': 5000,
            'reminder_time': '12:00',
            'reminder_type': 'weekly',
            'start_date': datetime.now() - timedelta(days=14),
            'last_reminder_date': None
        }
    
    @pytest.fixture
    def sample_rental_monthly(self):
        """Тестовая аренда с ежемесячным напоминанием"""
        return {
            'id': 3,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car',
            'daily_price': 5000,
            'reminder_time': '12:00',
            'reminder_type': 'monthly',
            'start_date': datetime.now() - timedelta(days=60),
            'last_reminder_date': None
        }
    
    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """Тест запуска планировщика"""
        await scheduler.start()
        
        assert scheduler.running is True
        assert scheduler._task is not None
        
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """Тест остановки планировщика"""
        await scheduler.start()
        await scheduler.stop()
        
        assert scheduler.running is False
    
    @pytest.mark.asyncio
    async def test_double_start(self, scheduler):
        """Тест двойного запуска (не должен создавать дубликаты)"""
        await scheduler.start()
        initial_task = scheduler._task
        
        await scheduler.start()  # Второй запуск
        
        assert scheduler._task == initial_task  # Задача не должна измениться
        
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_daily_first_time(self, scheduler, sample_rental_daily):
        """Тест отправки ежедневного напоминания в первый раз"""
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_daily, current_date)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_daily_already_sent_today(self, scheduler, sample_rental_daily):
        """Тест ежедневного напоминания, уже отправленного сегодня"""
        sample_rental_daily['last_reminder_date'] = date.today()
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_daily, current_date)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_daily_sent_yesterday(self, scheduler, sample_rental_daily):
        """Тест ежедневного напоминания, отправленного вчера"""
        sample_rental_daily['last_reminder_date'] = date.today() - timedelta(days=1)
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_daily, current_date)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_weekly_exact_7_days(self, scheduler, sample_rental_weekly):
        """Тест еженедельного напоминания ровно через 7 дней"""
        start_date = date.today() - timedelta(days=7)
        sample_rental_weekly['start_date'] = datetime.combine(start_date, datetime.min.time())
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_weekly, current_date)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_weekly_less_than_7_days(self, scheduler, sample_rental_weekly):
        """Тест еженедельного напоминания менее чем через 7 дней"""
        start_date = date.today() - timedelta(days=3)
        sample_rental_weekly['start_date'] = datetime.combine(start_date, datetime.min.time())
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_weekly, current_date)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_weekly_already_sent_this_week(self, scheduler, sample_rental_weekly):
        """Тест еженедельного напоминания, уже отправленного на этой неделе"""
        start_date = date.today() - timedelta(days=14)
        sample_rental_weekly['start_date'] = datetime.combine(start_date, datetime.min.time())
        sample_rental_weekly['last_reminder_date'] = date.today() - timedelta(days=3)
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_weekly, current_date)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_monthly_exact_30_days(self, scheduler, sample_rental_monthly):
        """Тест ежемесячного напоминания ровно через 30 дней"""
        start_date = date.today() - timedelta(days=30)
        sample_rental_monthly['start_date'] = datetime.combine(start_date, datetime.min.time())
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_monthly, current_date)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_send_reminder_monthly_less_than_30_days(self, scheduler, sample_rental_monthly):
        """Тест ежемесячного напоминания менее чем через 30 дней"""
        start_date = date.today() - timedelta(days=15)
        sample_rental_monthly['start_date'] = datetime.combine(start_date, datetime.min.time())
        current_date = date.today()
        
        result = await scheduler._should_send_reminder(sample_rental_monthly, current_date)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_reminder_daily(self, scheduler, sample_rental_daily):
        """Тест отправки ежедневного напоминания"""
        with patch('bot.utils.scheduler.update_rental_last_reminder', new_callable=AsyncMock) as mock_update:
            await scheduler._send_reminder(sample_rental_daily, date.today())
            
            scheduler.bot.send_message.assert_called_once()
            call_args = scheduler.bot.send_message.call_args
            assert call_args[1]['chat_id'] == sample_rental_daily['user_id']
            assert 'НАПОМИНАНИЕ ОБ ОПЛАТЕ' in call_args[1]['text']
            assert '5000' in call_args[1]['text']  # Ежедневная цена
            
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_reminder_weekly(self, scheduler, sample_rental_weekly):
        """Тест отправки еженедельного напоминания"""
        with patch('bot.utils.scheduler.update_rental_last_reminder', new_callable=AsyncMock):
            await scheduler._send_reminder(sample_rental_weekly, date.today())
            
            scheduler.bot.send_message.assert_called_once()
            call_args = scheduler.bot.send_message.call_args
            assert '35000' in call_args[1]['text']  # 5000 * 7 дней
    
    @pytest.mark.asyncio
    async def test_send_reminder_monthly(self, scheduler, sample_rental_monthly):
        """Тест отправки ежемесячного напоминания"""
        with patch('bot.utils.scheduler.update_rental_last_reminder', new_callable=AsyncMock):
            await scheduler._send_reminder(sample_rental_monthly, date.today())
            
            scheduler.bot.send_message.assert_called_once()
            call_args = scheduler.bot.send_message.call_args
            assert '150000' in call_args[1]['text']  # 5000 * 30 дней
    
    @pytest.mark.asyncio
    async def test_send_reminder_handles_exception(self, scheduler, sample_rental_daily):
        """Тест обработки исключений при отправке напоминания"""
        scheduler.bot.send_message.side_effect = Exception("Send error")
        
        # Не должно вызывать исключение
        await scheduler._send_reminder(sample_rental_daily, date.today())
        
        scheduler.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_reminder_invalid_start_date(self, scheduler, sample_rental_daily):
        """Тест обработки некорректной даты начала"""
        sample_rental_daily['start_date'] = "invalid_date"
        
        result = await scheduler._should_send_reminder(sample_rental_daily, date.today())
        
        assert result is False
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("reminder_type,days_since_start,expected", [
        ('daily', 0, True),
        ('daily', 1, True),
        ('daily', 5, True),
        ('weekly', 0, False),
        ('weekly', 3, False),
        ('weekly', 7, True),
        ('weekly', 14, True),
        ('monthly', 0, False),
        ('monthly', 15, False),
        ('monthly', 30, True),
        ('monthly', 60, True),
    ])
    async def test_reminder_types_various_scenarios(
        self, scheduler, reminder_type, days_since_start, expected
    ):
        """Параметризованный тест различных сценариев напоминаний"""
        rental = {
            'id': 1,
            'user_id': 123456789,
            'car_id': 1,
            'car_name': 'Test Car',
            'daily_price': 5000,
            'reminder_time': '12:00',
            'reminder_type': reminder_type,
            'start_date': datetime.combine(
                date.today() - timedelta(days=days_since_start),
                datetime.min.time()
            ),
            'last_reminder_date': None
        }
        
        result = await scheduler._should_send_reminder(rental, date.today())
        
        assert result == expected






