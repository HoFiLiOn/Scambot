import telebot
import json
import os
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TOKEN = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
ADMIN_ID = 7496116016

bot = telebot.TeleBot(TOKEN)

# ========== JSON БАЗА ==========
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"scams": [], "users": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ========== СОХРАНЕНИЕ ЮЗЕРА ==========
def save_user(user):
    data = load_db()
    
    found = False
    for u in data["users"]:
        if u["id"] == user.id:
            u["last_seen"] = str(datetime.now())
            u["username"] = user.username
            u["first_name"] = user.first_name
            found = True
            break
    
    if not found:
        data["users"].append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "first_seen": str(datetime.now()),
            "last_seen": str(datetime.now())
        })
    
    save_db(data)

# ========== ПРОВЕРКА В СКАМЕ ==========
def is_scam(username):
    username = username.lower().replace("@", "")
    data = load_db()
    for s in data["scams"]:
        if s["username"] == username:
            return True
    return False

# ========== ДОБАВИТЬ В СКАМ ==========
def add_to_scam(username, admin_id):
    username = username.lower().replace("@", "")
    data = load_db()
    
    for s in data["scams"]:
        if s["username"] == username:
            return False
    
    data["scams"].append({
        "username": username,
        "added_by": admin_id,
        "added_at": str(datetime.now())
    })
    
    save_db(data)
    return True

# ========== УДАЛИТЬ ИЗ СКАМА ==========
def remove_from_scam(username):
    username = username.lower().replace("@", "")
    data = load_db()
    
    for i, s in enumerate(data["scams"]):
        if s["username"] == username:
            data["scams"].pop(i)
            save_db(data)
            return True
    
    return False

# ========== ВСЕ СКАМЕРЫ ==========
def get_all_scams():
    data = load_db()
    return data["scams"]

# ========== НАЙТИ ЮЗЕРА ПО ID ==========
def get_user_by_id(user_id):
    data = load_db()
    for u in data["users"]:
        if u["id"] == user_id:
            return u
    return None

# ========== КОМАНДА СТАРТ ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = message.from_user
    save_user(user)
    
    bot.send_message(
        user.id,
        "👋 Привет! Я бот для проверки.\n\n"
        "🔍 Команды:\n"
        "/search @username - проверить по юзернейму\n"
        "/search 123456789 - проверить по ID\n"
        "/addscam @username - добавить в скам (только админ)\n"
        "/removescam @username - удалить из скам (только админ)\n"
        "/scamlist - список всех в скаме (только админ)"
    )

# ========== КОМАНДА ПОИСК ==========
@bot.message_handler(commands=['search'])
def search_cmd(message):
    user = message.from_user
    save_user(user)
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /search @username или /search 123456789")
            return
        
        query = parts[1].strip()
        
        # Если это ID (только цифры)
        if query.isdigit():
            user_id = int(query)
            found_user = get_user_by_id(user_id)
            
            if found_user:
                # Проверяем, есть ли в скаме
                if found_user.get('username') and is_scam(found_user['username']):
                    status = "🔴 В СКАМ-БАЗЕ!"
                else:
                    status = "🟢 ЧИСТ"
                
                bot.reply_to(
                    message,
                    f"🔍 Нашел по ID {user_id}:\n\n"
                    f"👤 Имя: {found_user['first_name']}\n"
                    f"📛 Юзернейм: @{found_user['username'] if found_user['username'] else 'нет'}\n"
                    f"📅 Заходил: {found_user['last_seen'][:19]}\n\n"
                    f"⚠️ Статус: {status}"
                )
            else:
                bot.reply_to(message, f"❌ Пользователь с ID {user_id} еще не заходил")
            return
        
        # Если это юзернейм
        username = query.lower().replace("@", "")
        
        if is_scam(username):
            bot.reply_to(
                message,
                f"🔴 @{username} В СКАМ-БАЗЕ!\n\n⚠️ МОШЕННИК!"
            )
        else:
            # Ищем в базе пользователей
            found = False
            data = load_db()
            for u in data["users"]:
                if u["username"] and u["username"].lower() == username:
                    bot.reply_to(
                        message,
                        f"🟢 @{username} НЕ В СКАМЕ\n\n"
                        f"👤 Имя: {u['first_name']}\n"
                        f"📅 Заходил: {u['last_seen'][:19]}"
                    )
                    found = True
                    break
            
            if not found:
                bot.reply_to(
                    message,
                    f"🟢 @{username} НЕ В СКАМЕ\n\n"
                    f"❓ Этот пользователь еще не заходил в бота"
                )
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['addscam'])
def addscam_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /addscam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if add_to_scam(username, ADMIN_ID):
            bot.reply_to(message, f"✅ @{username} добавлен в скам!")
        else:
            bot.reply_to(message, f"⚠️ @{username} уже в базе")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['removescam'])
def removescam_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /removescam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if remove_from_scam(username):
            bot.reply_to(message, f"✅ @{username} удален из скам!")
        else:
            bot.reply_to(message, f"⚠️ @{username} не найден")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['scamlist'])
def scamlist_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    scams = get_all_scams()
    
    if not scams:
        bot.reply_to(message, "📭 Скам-база пуста")
        return
    
    text = f"📋 Всего в скаме: {len(scams)}\n\n"
    for s in scams:
        text += f"• @{s['username']} (добавлен: {s['added_at'][:19]})\n"
    
    bot.reply_to(message, text)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🤖 Бот запущен!")
    print(f"👤 Админ ID: {ADMIN_ID}")
    bot.infinity_polling()