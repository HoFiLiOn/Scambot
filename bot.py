import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройки
TOKEN = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
ADMIN_ID = 7496116016

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация БД
def init_db():
    conn = sqlite3.connect("scam_database.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scams ("
        "username TEXT PRIMARY KEY, "
        "user_id INTEGER, "
        "added_by INTEGER, "
        "added_at TEXT"
        ")"
    )
    conn.commit()
    conn.close()

# Проверка наличия в базе по username
def is_in_scam_db(username: str) -> bool:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT 1 FROM scams WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Проверка наличия в базе по user_id
def is_user_id_in_scam_db(user_id: int) -> bool:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT 1 FROM scams WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Добавление в базу
def add_to_scam_db(username: str, user_id: int = None, admin_id: int = None) -> bool:
    if is_in_scam_db(username):
        return False
    
    admin_id = admin_id or ADMIN_ID
    conn = sqlite3.connect("scam_database.db")
    conn.execute(
        "INSERT INTO scams (username, user_id, added_by, added_at) VALUES (?, ?, ?, ?)",
        (username, user_id, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return True

# Удаление из базы
def remove_from_scam_db(username: str = None, user_id: int = None) -> bool:
    conn = sqlite3.connect("scam_database.db")
    if username:
        cursor = conn.execute("DELETE FROM scams WHERE username = ?", (username,))
    elif user_id:
        cursor = conn.execute("DELETE FROM scams WHERE user_id = ?", (user_id,))
    else:
        conn.close()
        return False
    
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

# Получение информации по user_id
def get_scam_by_user_id(user_id: int):
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT username, added_at FROM scams WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Получение информации по username
def get_scam_by_username(username: str):
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT user_id, added_at FROM scams WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result

# Получение списка
def get_scam_list() -> list:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT username, user_id, added_at FROM scams ORDER BY added_at")
    results = cursor.fetchall()
    conn.close()
    return results

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск по ID", callback_data="search_by_id")],
        [InlineKeyboardButton("🔍 Поиск по Username", callback_data="search_by_username")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 <b>Здравствуйте!</b> Я бот для проверки пользователей в скам-базе.\n\n"
        "<b>Как искать:</b>\n"
        "• По ID: нажмите кнопку ниже и введите ID\n"
        "• По Username: используйте /search @username\n"
        "• Или выберите нужный пункт в меню:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Обработка нажатий на кнопки
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "search_by_id":
        await query.edit_message_text(
            "🔍 <b>Поиск по ID</b>\n\n"
            "Введите ID пользователя (только цифры):\n"
            "Например: <code>123456789</code>\n\n"
            "Или отправьте /search_id 123456789",
            parse_mode="HTML"
        )
        context.user_data['awaiting_id'] = True
        
    elif query.data == "search_by_username":
        await query.edit_message_text(
            "🔍 <b>Поиск по Username</b>\n\n"
            "Используйте команду: /search @username\n"
            "Например: /search @durov",
            parse_mode="HTML"
        )
        
    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❓ <b>Помощь</b>\n\n"
            "<b>Команды:</b>\n"
            "/search @username - проверить по username\n"
            "/search_id 123456789 - проверить по ID\n\n"
            "<b>Для администраторов:</b>\n"
            "/addscam @username [id] - добавить в базу\n"
            "/removescam @username - удалить по username\n"
            "/removescam id:123456789 - удалить по ID\n"
            "/scamlist - список всех в базе",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    elif query.data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск по ID", callback_data="search_by_id")],
            [InlineKeyboardButton("🔍 Поиск по Username", callback_data="search_by_username")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👋 <b>Главное меню</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

# Команда /search @username
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используйте: /search @username")
        return

    username = context.args[0].strip().lower()
    if not username.startswith("@") or len(username) < 3:
        await update.message.reply_text("Укажите @username")
        return

    username = username[1:]  # Убираем @
    
    scam_info = get_scam_by_username(username)

    if scam_info:
        user_id, added_at = scam_info
        message = f"🔴 @{username} <b>— НАЙДЕН В СКАМ-БАЗЕ!</b>\n\n"
        message += f"📅 Добавлен: {added_at}\n"
        if user_id:
            message += f"🆔 ID: <code>{user_id}</code>\n\n"
        message += "<b>⚠️ Будьте осторожны! Этот человек в базе мошенников.</b>"
        
        await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"🟢 @{username} <b>— не найден в скам-базе</b>\n\n"
            "✅ По нашим данным, этот пользователь не числится в базе мошенников.",
            parse_mode="HTML"
        )

# Команда /search_id
async def search_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используйте: /search_id 123456789")
        return

    try:
        user_id = int(context.args[0].strip())
    except ValueError:
        await update.message.reply_text("ID должен содержать только цифры")
        return
    
    scam_info = get_scam_by_user_id(user_id)

    if scam_info:
        username, added_at = scam_info
        message = f"🔴 <b>НАЙДЕН В СКАМ-БАЗЕ!</b>\n\n"
        message += f"🆔 ID: <code>{user_id}</code>\n"
        message += f"📱 Username: @{username}\n"
        message += f"📅 Добавлен: {added_at}\n\n"
        message += "<b>⚠️ Будьте осторожны! Этот человек в базе мошенников.</b>"
        
        await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"🟢 <b>Не найден в скам-базе</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            "✅ По нашим данным, этот пользователь не числится в базе мошенников.",
            parse_mode="HTML"
        )

# Обработка текстовых сообщений (для поиска по ID)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_id', False):
        text = update.message.text.strip()
        
        # Проверяем, что это число
        if text.isdigit():
            user_id = int(text)
            scam_info = get_scam_by_user_id(user_id)
            
            if scam_info:
                username, added_at = scam_info
                message = f"🔴 <b>НАЙДЕН В СКАМ-БАЗЕ!</b>\n\n"
                message += f"🆔 ID: <code>{user_id}</code>\n"
                message += f"📱 Username: @{username}\n"
                message += f"📅 Добавлен: {added_at}\n\n"
                message += "<b>⚠️ Будьте осторожны! Этот человек в базе мошенников.</b>"
            else:
                message = f"🟢 <b>Не найден в скам-базе</b>\n\n🆔 ID: <code>{user_id}</code>"
            
            # Сбрасываем флаг
            context.user_data['awaiting_id'] = False
            
            # Добавляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Пожалуйста, введите только цифры (ID пользователя)")
    else:
        await update.message.reply_text("Используйте /start для начала работы")

# Команда /addscam (только для админа)
async def addscam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("Используйте: /addscam @username [id]")
        return

    username = context.args[0].strip().lower()
    if not username.startswith("@") or len(username) < 3:
        await update.message.reply_text("Укажите @username")
        return

    username = username[1:]
    
    # Проверяем, есть ли указан ID
    user_id = None
    if len(context.args) > 1:
        try:
            user_id = int(context.args[1])
        except ValueError:
            await update.message.reply_text("ID должен быть числом")
            return
    
    if add_to_scam_db(username, user_id):
        if user_id:
            await update.message.reply_text(f"✅ @{username} (ID: {user_id}) добавлен в базу.")
        else:
            await update.message.reply_text(f"✅ @{username} добавлен в базу.")
    else:
        await update.message.reply_text(f"⚠️ @{username} уже в базе.")

# Команда /removescam (только для админа)
async def removescam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("Используйте: /removescam @username или /removescam id:123456789")
        return

    arg = context.args[0].strip()
    
    if arg.startswith("id:"):
        # Удаление по ID
        try:
            user_id = int(arg[3:])
            if remove_from_scam_db(user_id=user_id):
                await update.message.reply_text(f"✅ Пользователь с ID {user_id} удалён из базы.")
            else:
                await update.message.reply_text(f"⚠️ Пользователь с ID {user_id} не найден в базе.")
        except ValueError:
            await update.message.reply_text("Неверный формат ID. Используйте: id:123456789")
    else:
        # Удаление по username
        if not arg.startswith("@") or len(arg) < 3:
            await update.message.reply_text("Укажите @username или id:123456789")
            return
        
        username = arg[1:].lower()
        if remove_from_scam_db(username=username):
            await update.message.reply_text(f"✅ @{username} удалён из базы.")
        else:
            await update.message.reply_text(f"⚠️ @{username} не найден в базе.")

# Команда /scamlist (только для админа)
async def scamlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    scams = get_scam_list()
    if not scams:
        await update.message.reply_text("База пуста.")
        return

    message = f"📋 <b>Список скамеров ({len(scams)}):</b>\n\n"
    for username, user_id, timestamp in scams:
        if user_id:
            message += f"• @{username} (ID: <code>{user_id}</code>) — {timestamp}\n"
        else:
            message += f"• @{username} — {timestamp}\n"
        
        # Если сообщение слишком длинное, отправляем частями
        if len(message) > 4000:
            await update.message.reply_text(message, parse_mode="HTML")
            message = ""

    if message:
        await update.message.reply_text(message, parse_mode="HTML")

# Обработка неизвестных команд
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используй /start")

# Запуск бота
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("search_id", search_id))
    app.add_handler(CommandHandler("addscam", addscam))
    app.add_handler(CommandHandler("removescam", removescam))
    app.add_handler(CommandHandler("scamlist", scamlist))
    
    # Обработчик callback-запросов (кнопки)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчик неизвестных команд
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Бот запущен...")
    print("✅ Бот успешно запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()