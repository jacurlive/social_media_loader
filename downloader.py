"""
Модуль для скачивания видео через yt-dlp
"""
import asyncio
import os
import yt_dlp
from datetime import datetime
from urllib.parse import quote
from config import (
    DOWNLOADS_DIR, logger,
    PROXY_IP, PROXY_PORT, PROXY_LOGIN, PROXY_PASSWORD, PROXY_TYPE, PROXY_TIMEOUT
)


async def download_video(url: str, platform: str):
    """
    Скачивание видео через yt-dlp
    
    Args:
        url: URL видео для скачивания
        platform: Платформа (instagram, tiktok, youtube, twitter, other)
    
    Returns:
        tuple: (filename, title, duration) или (None, None, None) при ошибке
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

        # Получаем информацию о видео
        title = info.get('title', 'Video')
        duration = info.get('duration', 0)

        return filename, title, duration

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при скачивании через yt-dlp: {error_msg}")
        
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
        
        return None, None, None

