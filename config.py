"""
Конфигурация бота
"""
import logging
import os
from dotenv import load_dotenv


load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Настройки базы данных
DATABASE_NAME = 'bot_database.db'

# Настройки загрузок
DOWNLOADS_DIR = 'downloads'
MAX_FILE_SIZE_MB = 50  # Лимит Telegram для ботов

# ID канала для хранения медиа (формат: @channel_username или -1001234567890)
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))  # ВАЖНО: Укажите ID вашего канала

# ID администратора для доступа к статистике
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # ВАЖНО: Укажите ваш Telegram user ID

# Настройки прокси для TikTok
PROXY_IP = os.getenv('PROXY_IP')  # ВАЖНО: Укажите IP адрес прокси-сервера
PROXY_PORT = int(os.getenv('PROXY_PORT'))  # ВАЖНО: Укажите порт прокси-сервера
PROXY_LOGIN = os.getenv('PROXY_LOGIN')  # ВАЖНО: Укажите логин для прокси (если требуется)
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')  # ВАЖНО: Укажите пароль для прокси (если требуется)
PROXY_TYPE = 'http'  # Тип прокси: 'http' или 'socks5'

# Настройки тайм-аутов для прокси (в секундах)
PROXY_TIMEOUT = 120  # Тайм-аут для подключения через прокси (увеличено до 120 секунд)
