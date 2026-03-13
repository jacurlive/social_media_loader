"""
Модуль для скачивания медиа через yt-dlp
"""
import asyncio
import os
import re
import aiohttp
import yt_dlp
from datetime import datetime
from urllib.parse import quote
from config import (
    DOWNLOADS_DIR, logger,
    PROXY_IP, PROXY_PORT, PROXY_LOGIN, PROXY_PASSWORD, PROXY_TYPE, PROXY_TIMEOUT
)


IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}


async def download_video(url: str, platform: str):
    """
    Скачивание медиа через yt-dlp (или tikwm для TikTok)

    Returns:
        tuple: (filename, title, duration, width, height, description, media_type)
               media_type: 'video' или 'image'
    """
    try:
        # Создаем папку для загрузок если её нет
        if not os.path.exists(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR)

        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_template = os.path.join(DOWNLOADS_DIR, f'{platform}_{timestamp}.%(ext)s')

        # Настройки для yt-dlp
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'geo_bypass': True,
            'socket_timeout': PROXY_TIMEOUT,  # Таймаут сокета
            'retries': 3,  # Количество попыток при ошибке
        }

        # Дополнительные настройки для Instagram
        if platform == 'instagram':
            ydl_opts['format'] = 'best[ext=mp4]/best'

        # Дополнительные настройки для Pinterest
        if platform == 'pinterest':
            ydl_opts['format'] = 'best'

        # Дополнительные настройки для TikTok
        if platform == 'tiktok':
            ydl_opts['format'] = 'best[ext=mp4]/best'
            # Улучшенный User-Agent для TikTok
            ydl_opts['http_headers'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Увеличиваем таймауты для TikTok через прокси
            ydl_opts['socket_timeout'] = PROXY_TIMEOUT
            ydl_opts['retries'] = 5  # Больше попыток для TikTok
            
            # Настройка прокси для TikTok
            if PROXY_IP and PROXY_PORT:
                # Формируем строку прокси с правильным экранированием
                if PROXY_LOGIN and PROXY_PASSWORD:
                    # Экранируем логин и пароль для безопасного использования в URL
                    encoded_login = quote(str(PROXY_LOGIN), safe='')
                    encoded_password = quote(str(PROXY_PASSWORD), safe='')
                    proxy_url = f"{PROXY_TYPE}://{encoded_login}:{encoded_password}@{PROXY_IP}:{PROXY_PORT}"
                else:
                    proxy_url = f"{PROXY_TYPE}://{PROXY_IP}:{PROXY_PORT}"
                
                # Устанавливаем прокси через параметр и переменные окружения
                ydl_opts['proxy'] = proxy_url
                
                # Устанавливаем переменные окружения для прокси (на случай если yt-dlp их использует)
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['http_proxy'] = proxy_url
                os.environ['https_proxy'] = proxy_url
                
                # Дополнительные настройки для работы через прокси
                ydl_opts['nocheckcertificate'] = True  # Не проверять SSL сертификаты через прокси
                ydl_opts['prefer_insecure'] = False  # Предпочитать безопасные соединения
                
                # Специальные настройки для TikTok экстрактора
                ydl_opts['extractor_args'] = {
                    'tiktok': {
                        'webpage_download_timeout': PROXY_TIMEOUT,
                        'api_hostname': 'api.tiktok.com',
                    }
                }
                
                logger.info(f"Используется прокси для TikTok: {PROXY_TYPE}://{PROXY_IP}:{PROXY_PORT}")
                logger.info(f"Таймаут установлен: {PROXY_TIMEOUT} секунд")
                logger.info(f"Прокси URL (без пароля): {PROXY_TYPE}://{PROXY_IP}:{PROXY_PORT}")

        # Скачивание в отдельном потоке чтобы не блокировать asyncio
        loop = asyncio.get_event_loop()

        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, info

        filename, info = await loop.run_in_executor(None, download_sync)

        # Получаем информацию о медиа
        title = info.get('title', 'Media')
        duration = info.get('duration', 0)
        width = info.get('width')
        height = info.get('height')
        description = info.get('description', '') or ''

        ext = os.path.splitext(filename)[1].lstrip('.').lower()
        media_type = 'image' if ext in IMAGE_EXTENSIONS else 'video'

        return filename, title, duration, width, height, description, media_type

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при скачивании через yt-dlp: {error_msg}")

        # Фолбэк для Pinterest: скачиваем изображение напрямую
        if platform == 'pinterest' and 'no video formats' in error_msg.lower():
            logger.info("Пробуем скачать Pinterest изображение напрямую...")
            return await _download_pinterest_image(url)

        # Дополнительная информация для отладки
        if platform == 'tiktok' and PROXY_IP and PROXY_PORT:
            logger.error(f"Прокси настроен: {PROXY_TYPE}://{PROXY_IP}:{PROXY_PORT}")
            logger.error(f"Таймаут: {PROXY_TIMEOUT} секунд")
            if 'timed out' in error_msg.lower():
                logger.error("Проблема: Таймаут при подключении через прокси. Возможные причины:")
                logger.error("1. Прокси-сервер не отвечает или заблокирован")
                logger.error("2. TikTok блокирует запросы через этот прокси")
                logger.error("3. Недостаточный таймаут (попробуйте увеличить PROXY_TIMEOUT)")
                logger.error("4. Попробуйте использовать socks5 вместо http (измените PROXY_TYPE)")

        return None, None, None, None, None, None, None


async def _download_pinterest_image(url: str):
    """Скачивание изображения Pinterest напрямую через HTTP"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                html = await resp.text()

        # Извлекаем og:image — наилучшее качество
        img_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if not img_match:
            # Альтернативный порядок атрибутов
            img_match = re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html)
        if not img_match:
            logger.error("Pinterest: не удалось найти og:image на странице")
            return None, None, None, None, None, None, None

        image_url = img_match.group(1)

        title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        title = title_match.group(1) if title_match else 'Pinterest'

        desc_match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
        description = desc_match.group(1) if desc_match else ''

        # Скачиваем изображение
        if not os.path.exists(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(image_url) as resp:
                content_type = resp.headers.get('content-type', 'image/jpeg')
                ext = 'jpg'
                if 'png' in content_type:
                    ext = 'png'
                elif 'webp' in content_type:
                    ext = 'webp'

                filename = os.path.join(DOWNLOADS_DIR, f'pinterest_{timestamp}.{ext}')
                with open(filename, 'wb') as f:
                    f.write(await resp.read())

        logger.info(f"Pinterest изображение скачано: {filename}")
        return filename, title, 0, None, None, description, 'image'

    except Exception as e:
        logger.error(f"Ошибка при прямом скачивании Pinterest изображения: {e}")
        return None, None, None, None, None, None, None

