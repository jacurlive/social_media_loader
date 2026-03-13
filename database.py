"""
Модуль для работы с базой данных
"""
import sqlite3
from datetime import datetime
from config import DATABASE_NAME


def init_db():
    """Инициализация базы данных и создание таблиц"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_date TEXT
        )
    ''')
    
    # Таблица медиа (скачанных видео)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            platform TEXT,
            channel_message_id INTEGER,
            title TEXT,
            duration INTEGER,
            file_size_mb REAL,
            download_date TEXT,
            description TEXT
        )
    ''')

    # Миграция: добавляем description если таблица уже существовала без неё
    try:
        cursor.execute('ALTER TABLE media ADD COLUMN description TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    # Старая таблица downloads (оставляем для совместимости со статистикой)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            url TEXT,
            platform TEXT,
            download_date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def add_user(user_id, username, first_name=None, last_name=None):
    """Добавление пользователя в базу данных (при /start)"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except sqlite3.IntegrityError:
        # Пользователь уже существует
        pass
    finally:
        conn.close()


def get_media_by_url(url):
    """Получение информации о медиа по URL"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id, url, channel_message_id, platform, description FROM media WHERE url = ?', (url,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'id': result[0],
            'url': result[1],
            'channel_message_id': result[2],
            'platform': result[3],
            'description': result[4] or '',
        }
    return None


def get_media_description(media_id):
    """Получение описания поста по ID медиа"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT description FROM media WHERE id = ?', (media_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] or '' if result else ''


def save_media(url, platform, channel_message_id, title=None, duration=None, file_size_mb=None, description=None):
    """Сохранение информации о скачанном медиа, возвращает id записи"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO media
            (url, platform, channel_message_id, title, duration, file_size_mb, download_date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (url, platform, channel_message_id, title, duration, file_size_mb,
              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), description))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_stats():
    """Получение статистики пользователей для админа"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Общее количество пользователей
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Количество уникальных пользователей, которые скачивали
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM downloads')
    active_users = cursor.fetchone()[0]
    
    # Общее количество медиа
    cursor.execute('SELECT COUNT(*) FROM media')
    total_media = cursor.fetchone()[0]
    
    # Статистика по платформам
    cursor.execute('SELECT platform, COUNT(*) FROM media GROUP BY platform')
    platform_stats = cursor.fetchall()
    
    # Топ пользователей по количеству скачиваний
    cursor.execute('''
        SELECT user_id, username, COUNT(*) as count 
        FROM downloads 
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    top_users = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'total_media': total_media,
        'platform_stats': platform_stats,
        'top_users': top_users
    }


def get_stats():
    """Получение общей статистики скачиваний (для обычных пользователей)"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM media')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM media WHERE platform = "tiktok"')
    tiktok = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM media WHERE platform = "instagram"')
    instagram = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM media WHERE platform = "youtube"')
    youtube = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'tiktok': tiktok,
        'instagram': instagram,
        'youtube': youtube
    }
