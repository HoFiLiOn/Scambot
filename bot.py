import telebot
import json
import os
from datetime import datetime

# ========== ТОКЕН ==========
TOKEN = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
bot = telebot.TeleBot(TOKEN)

# ========== АДМИН ==========
ADMIN_ID = 7496116016

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

# ========== СОХРАНИТЬ ПОЛЬЗОВАТЕЛЯ ==========
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

# ========== НАЙТИ ПО ID ==========
def get_user_by_id(user_id):
    data = load_db()
    for u in data["users"]:
        if u["id"] == user_id:
            return u
    return None

# ========== НАЙТИ ПО ЮЗЕРНЕЙМУ ==========
def get_user_by_username(username):
    username = username.lower().replace("@", "")
    data = load_db()
    for u in data["users"]:
        if u["username"] and u["username"].lower() == username:
            return u
    return None

# ========== КОМАНДА /start ==========
@bot.message_handler(commands=['start'])
def start_message(message):
    user = message.from_user
    save_user(user)
    
    text = f"👋 Привет, {user.first_name}!\n\n"
    text += "📋 Команды:\n"
    text += "/search @username - проверить по нику\n"
    text += "/search 123456789 - проверить по ID\n"
    text += "/help - помощь\n"
    
    if user.id == ADMIN_ID:
        text += "\n👑 Админ-команды:\n"
        text += "/addscam @username - добавить в скам\n"
        text += "/removescam @username - удалить из скам\n"
        text += "/scamlist - список скамеров\n"
    
    bot.send_message(message.chat.id, text)

# ========== КОМАНДА /help ==========
@bot.message_handler(commands=['help'])
def help_message(message):
    text = "❓ Помощь:\n\n"
    text += "/start - главное меню\n"
    text += "/search @username - проверить по нику\n"
    text += "/search 123456789 - проверить по ID\n"
    text += "/help - это сообщение"
    bot.send_message(message.chat.id, text)

# ========== КОМАНДА /search ==========
@bot.message_handler(commands=['search'])
def search_message(message):
    user = message.from_user
    save_user(user)
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши: /search @username или /search 123456789")
            return
        
        query = parts[1].strip()
        
        # Поиск по ID
        if query.isdigit():
            user_id = int(query)
            found = get_user_by_id(user_id)
            
            if found:
                if found.get('username') and is_scam(found['username']):
                    status = "🔴 В СКАМЕ!"
                else:
                    status = "🟢 ЧИСТ"
                
                text = f"🔍 Нашел по ID {user_id}:\n"
                text += f"👤 Имя: {found['first_name']}\n"
                text += f"📛 Ник: @{found['username'] if found['username'] else 'нет'}\n"
                text += f"📅 Заходил: {found['last_seen'][:19]}\n"
                text += f"⚠️ Статус: {status}"
            else:
                text = f"❌ Пользователь с ID {user_id} не найден"
            
            bot.reply_to(message, text)
            return
        
        # Поиск по нику
        username = query.lower().replace("@", "")
        
        if is_scam(username):
            text = f"🔴 @{username} В СКАМ-БАЗЕ!\n\n⚠️ МОШЕННИК!"
        else:
            found = get_user_by_username(username)
            if found:
                text = f"🟢 @{username} НЕ В СКАМЕ\n"
                text += f"👤 Имя: {found['first_name']}\n"
                text += f"📅 Заходил: {found['last_seen'][:19]}"
            else:
                text = f"🟢 @{username} НЕ В СКАМЕ\n\n❌ В боте не найден"
        
        bot.reply_to(message, text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== КОМАНДА /addscam (ТОЛЬКО АДМИН) ==========
@bot.message_handler(commands=['addscam'])
def addscam_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши: /addscam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if add_to_scam(username, ADMIN_ID):
            bot.reply_to(message, f"✅ @{username} добавлен в скам!")
        else:
            bot.reply_to(message, f"⚠️ @{username} уже в скаме")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== КОМАНДА /removescam (ТОЛЬКО АДМИН) ==========
@bot.message_handler(commands=['removescam'])
def removescam_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши: /removescam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if remove_from_scam(username):
            bot.reply_to(message, f"✅ @{username} удален из скама!")
        else:
            bot.reply_to(message, f"⚠️ @{username} не найден в скаме")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== КОМАНДА /scamlist (ТОЛЬКО АДМИН) ==========
@bot.message_handler(commands=['scamlist'])
def scamlist_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Это только для админа!")
        return
    
    scams = get_all_scams()
    
    if not scams:
        bot.reply_to(message, "📭 Скам-база пуста")
        return
    
    text = f"📋 Всего в скаме: {len(scams)}\n\n"
    for s in scams:
        text += f"• @{s['username']} ({s['added_at'][:16]})\n"
    
    bot.reply_to(message, text)

# ========== ЗАПУСК ==========
print("🚀 Бот запускается...")
print(f"👤 Админ ID: {ADMIN_ID}")
bot.infinity_polling()