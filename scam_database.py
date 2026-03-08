import sqlite3
from datetime import datetime

DB_PATH = "scam_database.db"

def get_db():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Создать все таблицы при первом запуске"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица скам-юзеров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scams (
            username TEXT PRIMARY KEY,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица пользователей бота
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных создана!")

# ========== РАБОТА СО СКАМ-БАЗОЙ ==========

def is_in_scam_db(username: str) -> bool:
    """Проверка наличия в базе"""
    username = username.lower().replace("@", "")
    conn = get_db()
    cursor = conn.execute("SELECT 1 FROM scams WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_to_scam_db(username: str, admin_id: int) -> bool:
    """Добавление в базу"""
    username = username.lower().replace("@", "")
    
    if is_in_scam_db(username):
        return False
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scams (username, added_by) VALUES (?, ?)",
        (username, admin_id)
    )
    conn.commit()
    conn.close()
    return True

def remove_from_scam_db(username: str) -> bool:
    """Удаление из базы"""
    username = username.lower().replace("@", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scams WHERE username = ?", (username,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_scam_list() -> list:
    """Получение списка всех скам-юзеров"""
    conn = get_db()
    cursor = conn.execute("SELECT username, added_at FROM scams ORDER BY added_at DESC")
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_scams_count() -> int:
    """Получить количество в скам-базе"""
    conn = get_db()
    cursor = conn.execute("SELECT COUNT(*) FROM scams")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

def save_user(user_id: int, username: str, first_name: str):
    """Сохранить или обновить пользователя в БД"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_seen)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (user_id, username, first_name))
    
    conn.commit()
    conn.close()

def get_all_users() -> list:
    """Получить всех пользователей бота"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT user_id, username, first_name, last_seen 
        FROM users 
        ORDER BY last_seen DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_users_count() -> int:
    """Получить количество пользователей"""
    conn = get_db()
    cursor = conn.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_today_count() -> int:
    """Получить количество активных сегодня"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT COUNT(*) FROM users 
        WHERE date(last_seen) = date('now')
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count