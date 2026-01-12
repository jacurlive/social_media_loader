"""
Точка входа в приложение
Главный файл для запуска бота
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, logger
from database import init_db
from handlers import register_handlers


async def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    logger.info("База данных инициализирована")

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация обработчиков
    register_handlers(dp, bot)

    # Удаление вебхуков и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен и готов к работе!")
    logger.info("Поддерживаемые платформы: TikTok, Instagram, YouTube, Twitter и другие")
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
