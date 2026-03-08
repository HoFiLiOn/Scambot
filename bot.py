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
    # Таблица для скамеров
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scams ("
        "username TEXT PRIMARY KEY, "
        "user_id INTEGER, "
        "added_by INTEGER, "
        "added_at TEXT"
        ")"
    )
    # Таблица для контактов пользователей
    conn.execute(
        "CREATE TABLE IF NOT EXISTS user_contacts ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_id INTEGER, "
        "contact_user_id INTEGER, "
        "contact_username TEXT, "
        "contact_first_name TEXT, "
        "contact_last_name TEXT, "
        "contact_phone TEXT, "
        "saved_at TEXT"
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

# Сохранение контакта
def save_user_contact(user_id: int, contact):
    conn = sqlite3.connect("scam_database.db")
    conn.execute(
        "INSERT INTO user_contacts (user_id, contact_user_id, contact_username, contact_first_name, contact_last_name, contact_phone, saved_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, contact.user_id, contact.username, contact.first_name, contact.last_name, contact.phone_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

# Получение контактов пользователя
def get_user_contacts(user_id: int) -> list:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute(
        "SELECT contact_user_id, contact_username, contact_first_name, contact_last_name, contact_phone, saved_at FROM user_contacts WHERE user_id = ? ORDER BY saved_at DESC",
        (user_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск по ID", callback_data="search_by_id")],
        [InlineKeyboardButton("📱 Мои контакты", callback_data="my_contacts")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 <b>Здравствуйте!</b> Я бот скам‑базы. Здесь вы найдёте актуальную информацию о мошеннических схемах и подозрительных ресурсах.\n\n"
        "<b>Команды:</b>\n"
        "/search @username — проверить по username\n"
        "Используйте кнопки ниже для дополнительных функций:",
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
            "Отправьте мне контакт человека, которого хотите проверить.\n"
            "Для этого нажмите на скрепку 📎 и выберите 'Контакт'.",
            parse_mode="HTML"
        )
        context.user_data['awaiting_contact'] = True
        
    elif query.data == "my_contacts":
        contacts = get_user_contacts(query.from_user.id)
        if not contacts:
            await query.edit_message_text(
                "📱 <b>Ваши контакты</b>\n\n"
                "У вас пока нет сохраненных контактов.\n"
                "Отправьте мне контакт человека, и я сохраню его для быстрой проверки.",
                parse_mode="HTML"
            )
        else:
            message = "📱 <b>Ваши контакты:</b>\n\n"
            for contact in contacts[:10]:  # Показываем последние 10
                user_id, username, first_name, last_name, phone, saved_at = contact
                name = f"{first_name} {last_name}".strip() or "Без имени"
                username_text = f" (@{username})" if username else ""
                status = "🔴 В СКАМ-БАЗЕ" if is_user_id_in_scam_db(user_id) else "🟢 Не в базе"
                
                message += f"• {name}{username_text}\n"
                message += f"  ID: <code>{user_id}</code>\n"
                message += f"  Статус: {status}\n"
                message += f"  Добавлен: {saved_at}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode="HTML", reply_markup=reply_markup)
            
    elif query.data == "help":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❓ <b>Помощь</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/search @username - проверить пользователя по username\n\n"
            "<b>Функции:</b>\n"
            "• Поиск по ID - отправьте контакт для проверки\n"
            "• Мои контакты - просмотр сохраненных контактов\n"
            "• При отправке контакта я автоматически проверяю его в базе\n\n"
            "<b>Для администраторов:</b>\n"
            "/addscam @username - добавить в скам-базу\n"
            "/removescam @username - удалить из базы\n"
            "/scamlist - список всех скамеров",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    elif query.data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск по ID", callback_data="search_by_id")],
            [InlineKeyboardButton("📱 Мои контакты", callback_data="my_contacts")],
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
        message = f"🔴 @{username} <b>— найден в скам базе!</b>\n\n"
        message += f"📅 Добавлен: {added_at}\n"
        if user_id:
            message += f"🆔 ID: <code>{user_id}</code>\n\n"
        message += "<b>Будьте осторожны и не доверяйте этой личности.</b>"
        
        await update.message.reply_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"🟢 @{username} <b>— не найден в скам базе.</b>\n\n"
            "<b>Это означает, что на данный момент нет информации о мошеннической деятельности данного пользователя.</b> "
            "Однако всегда будьте внимательны и осторожны при общении с незнакомыми людьми!",
            parse_mode="HTML"
        )

# Обработка полученных контактов
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id
    
    # Сохраняем контакт
    save_user_contact(user_id, contact)
    
    # Проверяем в скам-базе
    scam_info = get_scam_by_user_id(contact.user_id)
    
    if scam_info:
        username, added_at = scam_info
        message = f"🔴 <b>НАЙДЕН В СКАМ-БАЗЕ!</b>\n\n"
        message += f"👤 Имя: {contact.first_name} {contact.last_name or ''}\n"
        message += f"🆔 ID: <code>{contact.user_id}</code>\n"
        if contact.username:
            message += f"📱 Username: @{contact.username}\n"
        message += f"📅 Добавлен: {added_at}\n\n"
        message += "<b>⚠️ Будьте осторожны! Этот человек находится в базе мошенников.</b>"
    else:
        message = f"🟢 <b>Не найден в скам-базе</b>\n\n"
        message += f"👤 Имя: {contact.first_name} {contact.last_name or ''}\n"
        message += f"🆔 ID: <code>{contact.user_id}</code>\n"
        if contact.username:
            message += f"📱 Username: @{contact.username}\n\n"
        message += "✅ По нашим данным, этот человек не числится в базе мошенников."
    
    # Добавляем кнопки для дальнейших действий
    keyboard = [
        [InlineKeyboardButton("📱 Мои контакты", callback_data="my_contacts")],
        [InlineKeyboardButton("🔍 Проверить другой контакт", callback_data="search_by_id")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
    
    # Сбрасываем флаг ожидания контакта
    context.user_data['awaiting_contact'] = False

# Команда /addscam (только для админа)
async def addscam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("Используйте: /addscam @username [user_id]")
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
            pass
    
    if add_to_scam_db(username, user_id, ADMIN_ID):
        if user_id:
            await update.message.reply_text(f"✅ @{username} (ID: {user_id}) добавлен.")
        else:
            await update.message.reply_text(f"✅ @{username} добавлен.")
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
                await update.message.reply_text(f"✅ Пользователь с ID {user_id} удалён.")
            else:
                await update.message.reply_text(f"⚠️ Пользователь с ID {user_id} не найден.")
        except ValueError:
            await update.message.reply_text("Неверный формат ID. Используйте: id:123456789")
    else:
        # Удаление по username
        if not arg.startswith("@") or len(arg) < 3:
            await update.message.reply_text("Укажите @username или id:123456789")
            return
        
        username = arg[1:].lower()
        if remove_from_scam_db(username=username):
            await update.message.reply_text(f"✅ @{username} удалён.")
        else:
            await update.message.reply_text(f"⚠️ @{username} не найден.")

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

# Обработка неизвестных команд и сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, ожидаем ли мы контакт
    if context.user_data.get('awaiting_contact', False):
        await update.message.reply_text(
            "Пожалуйста, отправьте контакт, нажав на скрепку 📎 и выбрав 'Контакт'."
        )
    else:
        # Обработка обычных сообщений
        await update.message.reply_text(
            "Используйте команды или кнопки для работы со мной.\n"
            "/start - главное меню"
        )

# Запуск бота
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("addscam", addscam))
    app.add_handler(CommandHandler("removescam", removescam))
    app.add_handler(CommandHandler("scamlist", scamlist))
    
    # Обработчик callback-запросов (кнопки)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик контактов
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    
    # Обработчик обычных сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик неизвестных команд
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Бот запущен...")
    app.run_polling()

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используй /start")

if __name__ == "__main__":
    main()