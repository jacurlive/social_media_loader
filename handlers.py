"""
Обработчики команд и сообщений бота
"""
import os
from aiogram import F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import MAX_FILE_SIZE_MB, CHANNEL_ID, ADMIN_ID, logger
from database import (
    add_user, get_media_by_url, save_media,
    get_stats, get_user_stats, get_media_description
)
from downloader import download_video
from utils import detect_platform, format_duration


def _desc_keyboard(media_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Получить текст поста", callback_data=f"get_desc:{media_id}")
    ]])


def register_handlers(dp, bot: Bot):
    """Регистрация всех обработчиков"""
    
    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        # Добавляем пользователя в базу данных
        add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        
        await message.answer(
            "👋 Привет! Я бот для скачивания медиа из социальных сетей.\n\n"
            "📎 Просто отправь мне ссылку, и я скачаю медиа для тебя!\n\n"
            "Поддерживаемые платформы:\n"
            "📸 Instagram (посты, reels, IGTV)\n"
            "📌 Pinterest (фото, видео)\n\n"
            "Попробуй прямо сейчас! 🚀"
        )

    # @dp.message(F.text == "/stats")
    # async def cmd_stats(message: Message):
    #     """Обработчик команды /stats"""
    #     try:
    #         stats = get_stats()
    #         await message.answer(
    #             f"📊 Статистика бота:\n\n"
    #             f"Всего скачиваний: {stats['total']}\n"
    #             f"🎥 TikTok: {stats['tiktok']}\n"
    #             f"📸 Instagram: {stats['instagram']}\n"
    #             f"▶️ YouTube: {stats['youtube']}"
    #         )
    #     except Exception as e:
    #         logger.error(f"Ошибка при получении статистики: {e}")
    #         await message.answer("Ошибка при получении статистики")

    @dp.message(Command("admin_stats"))
    async def cmd_admin_stats(message: Message):
        """Обработчик команды /admin_stats для администратора"""
        if ADMIN_ID and message.from_user.id != ADMIN_ID:
            await message.answer("❌ У вас нет доступа к этой команде.")
            return
        
        try:
            stats = get_user_stats()
            
            # Формируем сообщение со статистикой
            text = "📊 Статистика пользователей:\n\n"
            text += f"👥 Всего пользователей: {stats['total_users']}\n"
            text += f"🔄 Активных пользователей: {stats['active_users']}\n"
            text += f"📹 Всего медиа: {stats['total_media']}\n\n"
            
            # Статистика по платформам
            if stats['platform_stats']:
                text += "📱 По платформам:\n"
                for platform, count in stats['platform_stats']:
                    platform_name = platform.capitalize() if platform else "Другие"
                    text += f"  • {platform_name}: {count}\n"
                text += "\n"
            
            # Топ пользователей
            if stats['top_users']:
                text += "🏆 Топ пользователей:\n"
                for idx, (user_id, username, count) in enumerate(stats['top_users'], 1):
                    username_display = username or f"ID: {user_id}"
                    text += f"  {idx}. {username_display}: {count} скачиваний\n"
            
            await message.answer(text)
        except Exception as e:
            logger.error(f"Ошибка при получении статистики админа: {e}")
            await message.answer("Ошибка при получении статистики")

    @dp.message(F.text)
    async def handle_url(message: Message):
        """Обработчик текстовых сообщений с ссылками"""
        url = message.text.strip()

        # Проверка, является ли сообщение URL
        if not url.startswith('http'):
            await message.answer("❌ Пожалуйста, отправьте корректную ссылку на видео")
            return

        # Проверяем, есть ли уже это видео в базе данных
        existing_media = get_media_by_url(url)
        
        if existing_media and CHANNEL_ID:
            # Видео уже есть в базе - пересылаем из канала
            try:
                await bot.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=CHANNEL_ID,
                    message_id=existing_media['channel_message_id']
                )
                if platform != 'pinterest':
                    await message.answer(
                        "Нажмите, чтобы получить текст поста 👇",
                        reply_markup=_desc_keyboard(existing_media['id'])
                    )
                return
            except Exception as e:
                logger.error(f"Ошибка при пересылке из канала: {e}")
                # Если не удалось переслать, продолжаем скачивание
                await message.answer("⚠️ Не удалось переслать из канала. Скачиваю заново...")

        platform = detect_platform(url)

        if not platform:
            await message.answer("❌ Пожалуйста, отправьте корректную ссылку на видео")
            return

        # Отправка сообщения о начале обработки
        status_msg = await message.answer("⏳ Начинаю скачивание...")

        try:
            # Скачиваем видео
            await status_msg.edit_text("📥 Скачиваю видео... Это может занять некоторое время.")

            filename, title, duration, width, height, description, media_type = await download_video(url, platform)

            if filename and os.path.exists(filename):
                # Проверяем размер файла
                file_size = os.path.getsize(filename)
                file_size_mb = file_size / (1024 * 1024)

                # Telegram имеет лимит 50 МБ для ботов
                if file_size_mb > MAX_FILE_SIZE_MB:
                    await status_msg.edit_text(
                        f"❌ Видео слишком большое ({file_size_mb:.1f} МБ).\n"
                        f"Максимальный размер: {MAX_FILE_SIZE_MB} МБ"
                    )
                    os.remove(filename)
                    return

                await status_msg.edit_text("📤 Отправляю видео...")

                # Формируем подпись для видео
                caption = f"✅ {title[:100]}\n\n"
                # if duration:
                #     caption += f"⏱ Длительность: {format_duration(duration)}\n"
                # caption += f"💾 Размер: {file_size_mb:.1f} МБ\n"
                # caption += f"📍 Платформа: {platform.capitalize()}\n\n"
                caption += "@LoadReelsBot"

                video_file = FSInputFile(filename)
                channel_message_id = None

                # Отправляем медиа в канал, если указан CHANNEL_ID
                if CHANNEL_ID:
                    try:
                        if media_type == 'image':
                            channel_msg = await bot.send_photo(
                                chat_id=CHANNEL_ID,
                                photo=video_file,
                                caption=caption
                            )
                        else:
                            channel_msg = await bot.send_video(
                                chat_id=CHANNEL_ID,
                                video=video_file,
                                caption=caption,
                                width=width,
                                height=height,
                                supports_streaming=True
                            )
                        channel_message_id = channel_msg.message_id
                    except Exception as e:
                        logger.error(f"Ошибка при отправке в канал: {e}")
                        await status_msg.edit_text(
                            "❌ Ошибка при отправке в канал. Проверьте настройки CHANNEL_ID."
                        )
                        os.remove(filename)
                        return

                # Сохраняем информацию о медиа в базу данных
                media_id = None
                if channel_message_id:
                    media_id = save_media(
                        url=url,
                        platform=platform,
                        channel_message_id=channel_message_id,
                        title=title,
                        duration=duration,
                        file_size_mb=file_size_mb,
                        description=description
                    )

                # Пересылаем медиа пользователю из канала или отправляем напрямую
                if CHANNEL_ID and channel_message_id:
                    await bot.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=CHANNEL_ID,
                        message_id=channel_message_id
                    )
                else:
                    # Если канал не настроен, отправляем напрямую
                    if media_type == 'image':
                        await message.answer_photo(video_file, caption=caption)
                    else:
                        await message.answer_video(
                            video_file,
                            caption=caption,
                            width=width,
                            height=height,
                            supports_streaming=True
                        )

                # Для фото дополнительно отправляем файл JPG
                if media_type == 'image':
                    await message.answer_document(FSInputFile(filename))

                # Удаляем статусное сообщение
                await status_msg.delete()

                # Кнопка текста поста — только не для Pinterest
                if media_id and platform != 'pinterest':
                    await message.answer(
                        "Нажмите, чтобы получить текст поста 👇",
                        reply_markup=_desc_keyboard(media_id)
                    )

                # Удаляем файл после отправки
                os.remove(filename)
            else:
                await status_msg.edit_text(
                    "❌ Не удалось скачать видео. Возможные причины:\n"
                    "• Приватный аккаунт\n"
                    "• Неверная ссылка\n"
                    "• Видео удалено\n"
                    "• Неподдерживаемая платформа\n"
                    "• Видео защищено от скачивания\n\n"
                    "Попробуйте другую ссылку."
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке: {e}")
            await status_msg.edit_text(
                f"❌ Произошла ошибка при скачивании.\n"
                f"Ошибка: {str(e)[:100]}\n\n"
                f"Попробуйте позже или отправьте другую ссылку."
            )

    @dp.callback_query(F.data.startswith("get_desc:"))
    async def callback_get_desc(callback: CallbackQuery):
        """Показать текст поста по нажатию кнопки"""
        media_id = int(callback.data.split(":")[1])
        description = get_media_description(media_id)

        text = description.strip() if description.strip() else "Описание отсутствует"
        await callback.message.edit_text(text, reply_markup=None)
        await callback.answer()
