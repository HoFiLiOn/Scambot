import sqlite3
import os
from datetime import datetime
from config import DB_PATH

def get_db():
    """Получить соединение с БД"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
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
    
    # Таблица логов действий админов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных создана!")

# ========== ПРОВЕРКА АДМИНА ==========

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    from config import ADMINS
    return user_id in ADMINS

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
    
    # Логируем действие
    log_admin_action(admin_id, "ADD_SCAM", username)
    
    return True

def remove_from_scam_db(username: str, admin_id: int) -> bool:
    """Удаление из базы"""
    username = username.lower().replace("@", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scams WHERE username = ?", (username,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        log_admin_action(admin_id, "REMOVE_SCAM", username)
    
    return deleted

def get_scam_list(limit: int = 100, offset: int = 0) -> list:
    """Получение списка всех скам-юзеров с пагинацией"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT username, added_at, added_by 
        FROM scams 
        ORDER BY added_at DESC 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def search_scam(query: str) -> list:
    """Поиск по скам-базе"""
    query = f"%{query.lower()}%"
    conn = get_db()
    cursor = conn.execute("""
        SELECT username, added_at, added_by 
        FROM scams 
        WHERE username LIKE ? 
        ORDER BY added_at DESC
    """, (query,))
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

def get_user_by_id(user_id: int) -> dict:
    """Получить пользователя по ID"""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_username(username: str) -> dict:
    """Получить пользователя по username"""
    username = username.lower().replace("@", "")
    conn = get_db()
    cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users(limit: int = 100, offset: int = 0) -> list:
    """Получить всех пользователей бота с пагинацией"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT user_id, username, first_name, last_seen 
        FROM users 
        ORDER BY last_seen DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def search_users(query: str) -> list:
    """Поиск пользователей по имени или юзернейму"""
    query = f"%{query}%"
    conn = get_db()
    cursor = conn.execute("""
        SELECT user_id, username, first_name, last_seen 
        FROM users 
        WHERE username LIKE ? OR first_name LIKE ?
        ORDER BY last_seen DESC
    """, (query, query))
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

def get_active_week_count() -> int:
    """Получить количество активных за неделю"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT COUNT(*) FROM users 
        WHERE last_seen >= datetime('now', '-7 days')
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_month_count() -> int:
    """Получить количество активных за месяц"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT COUNT(*) FROM users 
        WHERE last_seen >= datetime('now', '-30 days')
    """)
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ========== ЛОГИ АДМИНОВ ==========

def log_admin_action(admin_id: int, action: str, target: str = None):
    """Записать действие админа в лог"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admin_logs (admin_id, action, target) VALUES (?, ?, ?)",
        (admin_id, action, target)
    )
    conn.commit()
    conn.close()

def get_admin_logs(limit: int = 50) -> list:
    """Получить последние действия админов"""
    conn = get_db()
    cursor = conn.execute("""
        SELECT admin_id, action, target, timestamp 
        FROM admin_logs 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_admin_stats(admin_id: int = None) -> dict:
    """Получить статистику действий админов"""
    conn = get_db()
    
    if admin_id:
        cursor = conn.execute("""
            SELECT action, COUNT(*) as count 
            FROM admin_logs 
            WHERE admin_id = ? 
            GROUP BY action
        """, (admin_id,))
    else:
        cursor = conn.execute("""
            SELECT admin_id, action, COUNT(*) as count 
            FROM admin_logs 
            GROUP BY admin_id, action
        """)
    
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]