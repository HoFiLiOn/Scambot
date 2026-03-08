import telebot
from telebot import types
import json
import os
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TOKEN = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
ADMIN_ID = 7496116016  # Владелец
MY_ID = 7040677455     # Твой ID

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

# ========== ПРОВЕРКА АДМИНА ==========
def is_admin(user_id):
    return user_id == ADMIN_ID or user_id == MY_ID  # Оба админы

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
    
    # Проверяем есть ли уже
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

# ========== НАЙТИ ЮЗЕРА ПО ЮЗЕРНЕЙМУ ==========
def get_user_by_username(username):
    username = username.lower().replace("@", "")
    data = load_db()
    for u in data["users"]:
        if u["username"] and u["username"].lower() == username:
            return u
    return None

# ========== ВСЕ ЮЗЕРЫ ==========
def get_all_users(limit=10):
    data = load_db()
    users = sorted(data["users"], key=lambda x: x["last_seen"], reverse=True)
    return users[:limit]

# ========== СТАТИСТИКА ==========
def get_stats():
    data = load_db()
    return {
        "users": len(data["users"]),
        "scams": len(data["scams"])
    }

# ========== КОМАНДА СТАРТ ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = message.from_user
    save_user(user)
    
    # Если админ - показываем админ-меню
    if is_admin(user.id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            types.InlineKeyboardButton("👥 Юзеры", callback_data="users"),
            types.InlineKeyboardButton("📋 Скам-список", callback_data="scamlist"),
            types.InlineKeyboardButton("➕ Добавить в скам", callback_data="add_scam"),
            types.InlineKeyboardButton("➖ Удалить из скам", callback_data="remove_scam"),
            types.InlineKeyboardButton("🔍 Поиск юзера", callback_data="search_user")
        )
        
        bot.send_message(
            user.id,
            f"👋 Привет, админ {user.first_name}!\n\n"
            f"🆔 Твой ID: {user.id}\n"
            f"👤 Админ ID: {ADMIN_ID}\n"
            f"👤 Твой ID: {MY_ID}\n\n"
            f"Выбери действие:",
            reply_markup=markup
        )
    else:
        # Обычный пользователь
        bot.send_message(
            user.id,
            "👋 Привет! Я бот для проверки мошенников.\n\n"
            "🔍 Команды:\n"
            "/search @username - проверить по юзернейму\n"
            "/search 123456789 - проверить по ID\n"
            "/help - помощь"
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
                    status = "🔴 В СКАМ-БАЗЕ! МОШЕННИК!"
                else:
                    status = "🟢 ЧИСТ (не найден в скаме)"
                
                bot.reply_to(
                    message,
                    f"🔍 Нашел пользователя по ID {user_id}:\n\n"
                    f"👤 Имя: {found_user['first_name']}\n"
                    f"📛 Юзернейм: @{found_user['username'] if found_user['username'] else 'нет'}\n"
                    f"📅 Заходил: {found_user['last_seen'][:19]}\n\n"
                    f"⚠️ Статус: {status}"
                )
            else:
                bot.reply_to(message, f"❌ Пользователь с ID {user_id} еще не пользовался ботом")
            return
        
        # Если это юзернейм
        username = query.lower().replace("@", "")
        
        if is_scam(username):
            bot.reply_to(
                message,
                f"🔴 @{username} НАЙДЕН В СКАМ-БАЗЕ!\n\n"
                f"⚠️ МОШЕННИК! Не общайся, не переводи деньги!"
            )
        else:
            bot.reply_to(
                message,
                f"🟢 @{username} НЕ НАЙДЕН в скам-базе\n\n"
                f"✅ По нашим данным безопасен, но будь осторожен!"
            )
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== КОМАНДА ПОМОЩЬ ==========
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(
        message,
        "📚 Помощь:\n\n"
        "/start - главное меню\n"
        "/search @username - проверить по юзернейму\n"
        "/search 123456789 - проверить по ID\n"
        "/help - это сообщение"
    )

# ========== АДМИН-КОМАНДЫ ==========
@bot.message_handler(commands=['addscam'])
def addscam_cmd(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ У тебя нет прав админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /addscam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if add_to_scam(username, user_id):
            bot.reply_to(message, f"✅ @{username} добавлен в скам-базу!")
        else:
            bot.reply_to(message, f"⚠️ @{username} уже есть в скам-базе")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['removescam'])
def removescam_cmd(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ У тебя нет прав админа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /removescam @username")
            return
        
        username = parts[1].strip().lower().replace("@", "")
        
        if remove_from_scam(username):
            bot.reply_to(message, f"✅ @{username} удален из скам-базы!")
        else:
            bot.reply_to(message, f"⚠️ @{username} не найден в скам-базе")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['scamlist'])
def scamlist_cmd(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ У тебя нет прав админа!")
        return
    
    scams = get_all_scams()
    
    if not scams:
        bot.reply_to(message, "📭 Скам-база пуста")
        return
    
    text = f"📋 Всего в скам-базе: {len(scams)}\n\n"
    for s in scams[:20]:  # Покажем первые 20
        text += f"• @{s['username']} (добавлен: {s['added_at'][:19]})\n"
    
    bot.reply_to(message, text)

# ========== ОБРАБОТКА КНОПОК ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ Это только для админов!")
        return
    
    data = call.data
    
    if data == "stats":
        stats = get_stats()
        bot.edit_message_text(
            f"📊 Статистика:\n\n"
            f"👥 Всего юзеров: {stats['users']}\n"
            f"🔴 В скам-базе: {stats['scams']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Назад", callback_data="back")
            )
        )
    
    elif data == "users":
        users = get_all_users(10)
        text = "👥 Последние 10 юзеров:\n\n"
        for u in users:
            username = f"@{u['username']}" if u['username'] else "нет юзернейма"
            text += f"• {u['first_name']} ({username})\n"
            text += f"  ID: {u['id']}\n"
            text += f"  Был: {u['last_seen'][:19]}\n\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Назад", callback_data="back")
            )
        )
    
    elif data == "scamlist":
        scams = get_all_scams()
        if not scams:
            bot.edit_message_text(
                "📭 Скам-база пуста",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back")
                )
            )
            return
        
        text = f"📋 Всего в скаме: {len(scams)}\n\n"
        for s in scams[:10]:
            text += f"• @{s['username']}\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Назад", callback_data="back")
            )
        )
    
    elif data == "add_scam":
        bot.edit_message_text(
            "➕ Отправь мне @username кого добавить в скам",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Отмена", callback_data="back")
            )
        )
        # Тут нужно добавить обработку следующего сообщения
    
    elif data == "remove_scam":
        bot.edit_message_text(
            "➖ Отправь мне @username кого удалить из скам",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Отмена", callback_data="back")
            )
        )
    
    elif data == "search_user":
        bot.edit_message_text(
            "🔍 Отправь мне ID или @username для поиска",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("◀️ Отмена", callback_data="back")
            )
        )
    
    elif data == "back":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            types.InlineKeyboardButton("👥 Юзеры", callback_data="users"),
            types.InlineKeyboardButton("📋 Скам-список", callback_data="scamlist"),
            types.InlineKeyboardButton("➕ Добавить в скам", callback_data="add_scam"),
            types.InlineKeyboardButton("➖ Удалить из скам", callback_data="remove_scam"),
            types.InlineKeyboardButton("🔍 Поиск юзера", callback_data="search_user")
        )
        
        bot.edit_message_text(
            "👋 Админ-панель\n\nВыбери действие:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    bot.answer_callback_query(call.id)

# ========== ОБРАБОТКА ТЕКСТА ==========
@bot.message_handler(func=lambda message: True)
def text_handler(message):
    user_id = message.from_user.id
    
    # Проверяем, что это админ и что-то пишет после кнопок
    if is_admin(user_id):
        # Тут можно добавить логику для обработки текста после нажатия кнопок
        # Например, добавление в скам через текст
        pass

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🤖 Бот запущен!")
    print(f"👤 Админ ID: {ADMIN_ID}")
    print(f"👤 Твой ID: {MY_ID}")
    print("✅ Оба админы!")
    bot.infinity_polling()