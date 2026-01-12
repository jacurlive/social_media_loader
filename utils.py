"""
Вспомогательные функции
"""
from typing import Optional


def detect_platform(url: str) -> Optional[str]:
    """Определение платформы по URL"""
    url_lower = url.lower()
    if 'instagram.com' in url_lower or 'instagr.am' in url_lower:
        return 'instagram'
    # elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
    #     return 'tiktok'
    # elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
    #     return 'youtube'
    # elif 'twitter.com' in url_lower or 'x.com' in url_lower:
    #     return 'twitter'
    return None


def format_duration(seconds):
    """Форматирование длительности видео в формат ММ:СС"""
    if not seconds:
        return "неизвестно"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

