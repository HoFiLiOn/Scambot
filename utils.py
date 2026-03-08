import re
from datetime import datetime

def format_number(num: int) -> str:
    """Форматирование чисел (1000 -> 1,000)"""
    return f"{num:,}"

def format_timestamp(timestamp: str) -> str:
    """Форматирование временной метки"""
    if not timestamp:
        return "никогда"
    
    try:
        dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
        now = datetime.now()
        delta = now - dt
        
        if delta.days > 30:
            return dt.strftime("%d.%m.%Y")
        elif delta.days > 0:
            return f"{delta.days} дн. назад"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} ч. назад"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} мин. назад"
        else:
            return "только что"
    except:
        return timestamp

def extract_username(text: str) -> str:
    """Извлечь username из текста"""
    # Удаляем @ и пробелы
    username = text.strip().lower().replace("@", "")
    
    # Оставляем только допустимые символы
    username = re.sub(r'[^a-zA-Z0-9_]', '', username)
    
    return username

def is_valid_username(username: str) -> bool:
    """Проверка валидности username"""
    if len(username) < 2 or len(username) > 32:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))

def split_message(text: str, max_length: int = 3500) -> list:
    """Разбить длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Ищем место для разрыва
        split_point = text.rfind('\n', 0, max_length)
        if split_point == -1:
            split_point = text.rfind(' ', 0, max_length)
        if split_point == -1:
            split_point = max_length
        
        parts.append(text[:split_point])
        text = text[split_point:].lstrip()
    
    return parts