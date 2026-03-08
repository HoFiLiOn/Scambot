import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from config import TOKEN, ADMINS, VERSION
import database
import utils

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ ==========

# Создаем базу данных при запуске
database.init_database()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in ADMINS

def get_admin_keyboard():
    """Клавиатура для админ-панели"""
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_search_user")],
        [InlineKeyboardButton("📋 Скам-список", callback_data="admin_scamlist")],
        [InlineKeyboardButton("➕ Добавить в скам", callback_data="admin_add_scam")],
        [InlineKeyboardButton("➖ Удалить из скам", callback_data="admin_remove_scam")],
        [InlineKeyboardButton("🔎 Поиск по скам", callback_data="admin_search_scam")],
        [InlineKeyboardButton("📨 Рассылка", callback_data="admin_mail")],
        [InlineKeyboardButton("📜 Логи админов", callback_data="admin_logs")],
        [InlineKeyboardButton("📈 Моя статистика", callback_data="admin_my_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    database.save_user(user.id, user.username, user.first_name)
    
    # Если это админ - показываем админ-панель
    if is_admin(user.id):
        await update.message.reply_text(
            f"👋 <b>Здравствуйте, администратор!</b>\n\n"
            f"🆔 Ваш ID: <code>{user.id}</code>\n"
            f"📊 Версия бота: {VERSION}\n\n"
            f"Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Обычным пользователям обычное приветствие
        await update.message.reply_text(
            "👋 <b>Здравствуйте!</b>\n\n"
            "Я бот для проверки мошенников 🔍\n\n"
            "<b>Команды:</b>\n"
            "/search @username — проверить по юзернейму\n"
            "/search 123456789 — проверить по ID\n"
            "/help — помощь",
            parse_mode="HTML"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📚 <b>Помощь по боту</b>\n\n"
        "<b>🔍 Поиск:</b>\n"
        "/search @username — проверить по юзернейму\n"
        "/search 123456789 — проверить по ID\n\n"
        "<b>📋 Другое:</b>\n"
        "/start — главное меню\n"
        "/help — это сообщение\n\n"
        "<b>⚠️ Если вы нашли мошенника:</b>\n"
        "Сообщите администратору",
        parse_mode="HTML"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск по username или ID"""
    user = update.effective_user
    database.save_user(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n"
            "Используйте: /search @username или /search 123456789",
            parse_mode="HTML"
        )
        return

    query = context.args[0].strip()
    
    # Если это ID (только цифры)
    if query.isdigit():
        user_id = int(query)
        
        # Ищем в базе пользователей
        found_user = database.get_user_by_id(user_id)
        
        if found_user:
            # Проверяем, есть ли в скам-базе
            if found_user.get('username') and database.is_in_scam_db(found_user['username']):
                status = "🔴 НАЙДЕН В СКАМ!"
                safety = "❌ МОШЕННИК!"
            else:
                status = "🟢 НЕ НАЙДЕН"
                safety = "✅ Безопасен"
            
            await update.message.reply_text(
                f"🔍 <b>Результат поиска по ID:</b> <code>{user_id}</code>\n\n"
                f"👤 <b>Информация:</b>\n"
                f"• Имя: {found_user['first_name']}\n"
                f"• Юзернейм: @{found_user['username'] if found_user['username'] else 'нет'}\n"
                f"• Последний вход: {utils.format_timestamp(found_user['last_seen'])}\n\n"
                f"📊 <b>Статус:</b> {status}\n"
                f"⚠️ <b>Вердикт:</b> {safety}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text(
                f"🔍 <b>Поиск по ID:</b> <code>{query}</code>\n\n"
                f"❌ Пользователь с таким ID еще не пользовался ботом.\n"
                f"🟢 По нашим данным - безопасен.",
                parse_mode="HTML"
            )
        return
    
    # Если это username
    username = utils.extract_username(query)
    
    if not utils.is_valid_username(username):
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n"
            "Некорректный username",
            parse_mode="HTML"
        )
        return

    if database.is_in_scam_db(username):
        # Получаем информацию о том, кто добавил
        scams = database.search_scam(username)
        added_by = "неизвестно"
        added_at = "неизвестно"
        
        if scams:
            added_by_id = scams[0].get('added_by')
            added_at = scams[0].get('added_at', 'неизвестно')
            
            # Пытаемся получить имя админа
            admin = database.get_user_by_id(added_by_id) if added_by_id else None
            if admin:
                added_by = f"@{admin['username']}" if admin['username'] else f"ID: {added_by_id}"
            else:
                added_by = f"ID: {added_by_id}"
        
        await update.message.reply_text(
            f"🔴 <b>⚠️ ВНИМАНИЕ! ⚠️</b>\n\n"
            f"Пользователь <b>@{username}</b> <u>НАЙДЕН В СКАМ БАЗЕ!</u>\n\n"
            f"📅 Добавлен: {added_at[:16]}\n"
            f"👮 Добавил: {added_by}\n\n"
            f"❌ <b>МОШЕННИК!</b>\n"
            f"Не доверяйте этому человеку, не переводите деньги, не передавайте личные данные.\n\n"
            f"🚫 <b>Рекомендуем:</b>\n"
            f"• Заблокировать\n"
            f"• Пожаловаться\n"
            f"• Игнорировать",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"🟢 <b>✅ БЕЗОПАСНО</b>\n\n"
            f"Пользователь <b>@{username}</b> <u>НЕ НАЙДЕН</u> в скам базе.\n\n"
            f"По нашим данным это безопасный пользователь.\n\n"
            f"⚠️ <b>Но помните:</b>\n"
            f"Всегда будьте бдительны при общении с незнакомцами!",
            parse_mode="HTML"
        )

# ========== АДМИН-КОМАНДЫ ==========

async def addscam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить в скам-базу"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ <b>Доступ запрещён</b>", parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ <b>Используйте:</b> /addscam @username",
            parse_mode="HTML"
        )
        return

    username = utils.extract_username(context.args[0])
    
    if not utils.is_valid_username(username):
        await update.message.reply_text(
            "❌ <b>Ошибка</b>\n"
            "Некорректный username",
            parse_mode="HTML"
        )
        return

    if database.add_to_scam_db(username, update.effective_user.id):
        await update.message.reply_text(
            f"✅ <b>Готово!</b>\n"
            f"Пользователь @{username} добавлен в скам-базу.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"⚠️ <b>Внимание!</b>\n"
            f"Пользователь @{username} уже есть в базе.",
            parse_mode="HTML"
        )

async def removescam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить из скам-базы"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ <b>Доступ запрещён</b>", parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ <b>Используйте:</b> /removescam @username",
            parse_mode="HTML"
        )
        return

    username = utils.extract_username(context.args[0])

    if database.remove_from_scam_db(username, update.effective_user.id):
        await update.message.reply_text(
            f"✅ <b>Готово!</b>\n"
            f"Пользователь @{username} удалён из скам-базы.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"⚠️ <b>Внимание!</b>\n"
            f"Пользователь @{username} не найден в базе.",
            parse_mode="HTML"
        )

async def scamlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать весь скам-список"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ <b>Доступ запрещён</b>", parse_mode="HTML")
        return

    # Получаем параметры пагинации
    page = 1
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])
    
    limit = 20
    offset = (page - 1) * limit
    
    scams = database.get_scam_list(limit, offset)
    total = database.get_scams_count()
    total_pages = (total + limit - 1) // limit
    
    if not scams:
        await update.message.reply_text(
            "📭 <b>Скам-база пуста</b>\n\n"
            "Пока нет добавленных мошенников.",
            parse_mode="HTML"
        )
        return

    # Формируем сообщение
    message = f"📋 <b>Скам-список (страница {page}/{total_pages})</b>\n"
    message += f"Всего в базе: {total}\n\n"
    
    for scam in scams:
        admin = database.get_user_by_id(scam['added_by'])
        admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {scam['added_by']}"
        
        message += f"• @{scam['username']}\n"
        message += f"  👮 Добавил: {admin_name}\n"
        message += f"  📅 {scam['added_at'][:16]}\n\n"
    
    # Кнопки навигации
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"scamlist_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"scamlist_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")])
    
    await update.message.reply_text(
        message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

# ========== АДМИН-ПАНЕЛЬ (ОБРАБОТЧИКИ КНОПОК) ==========

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    await query.answer()
    
    users_count = database.get_users_count()
    scams_count = database.get_scams_count()
    active_today = database.get_active_today_count()
    active_week = database.get_active_week_count()
    active_month = database.get_active_month_count()
    
    # Статистика по админам
    admin_stats = database.get_admin_stats()
    
    stats_text = (
        f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Всего пользователей: <b>{utils.format_number(users_count)}</b>\n"
        f"📅 Активных сегодня: <b>{utils.format_number(active_today)}</b>\n"
        f"📆 Активных за неделю: <b>{utils.format_number(active_week)}</b>\n"
        f"📅 Активных за месяц: <b>{utils.format_number(active_month)}</b>\n"
        f"🔴 В скам-базе: <b>{utils.format_number(scams_count)}</b>\n\n"
        f"📦 <b>База данных:</b> SQLite\n"
        f"📁 Файл: scam_database.db\n"
        f"🤖 Версия: {VERSION}\n\n"
    )
    
    if admin_stats:
        stats_text += "<b>👮 Активность админов:</b>\n"
        for stat in admin_stats[:5]:
            admin = database.get_user_by_id(stat['admin_id'])
            admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {stat['admin_id']}"
            stats_text += f"• {admin_name}: {stat['count']} действий\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]]
    
    await query.edit_message_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей"""
    query = update.callback_query
    await query.answer()
    
    users = database.get_all_users(limit=10)
    total = database.get_users_count()
    
    if not users:
        await query.edit_message_text(
            "📭 <b>Нет пользователей</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")
            ]])
        )
        return

    message = f"👥 <b>Последние пользователи (первые 10 из {total})</b>\n\n"
    
    for user in users:
        username_str = f"@{user['username']}" if user['username'] else "нет юзернейма"
        message += f"• {user['first_name']} ({username_str})\n"
        message += f"  ID: <code>{user['user_id']}</code>\n"
        message += f"  Последний вход: {utils.format_timestamp(user['last_seen'])}\n\n"

    keyboard = [
        [InlineKeyboardButton("🔍 Поиск", callback_data="admin_search_user")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать поиск пользователя"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'search_user'
    
    await query.edit_message_text(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Отправь мне ID или @username пользователя:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="back_to_admin")
        ]])
    )

async def admin_add_scam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать добавление в скам"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'add_scam'
    
    await query.edit_message_text(
        "➕ <b>Добавление в скам-базу</b>\n\n"
        "Отправь мне @username мошенника:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="back_to_admin")
        ]])
    )

async def admin_remove_scam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать удаление из скам"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'remove_scam'
    
    await query.edit_message_text(
        "➖ <b>Удаление из скам-базы</b>\n\n"
        "Отправь мне @username для удаления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="back_to_admin")
        ]])
    )

async def admin_search_scam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск по скам-базе"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'search_scam'
    
    await query.edit_message_text(
        "🔎 <b>Поиск по скам-базе</b>\n\n"
        "Отправь мне username для поиска:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="back_to_admin")
        ]])
    )

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать логи админов"""
    query = update.callback_query
    await query.answer()
    
    logs = database.get_admin_logs(20)
    
    if not logs:
        await query.edit_message_text(
            "📭 <b>Логи пусты</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")
            ]])
        )
        return

    message = "📜 <b>Последние действия админов:</b>\n\n"
    
    for log in logs:
        admin = database.get_user_by_id(log['admin_id'])
        admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {log['admin_id']}"
        
        action_emoji = {
            'ADD_SCAM': '➕',
            'REMOVE_SCAM': '➖',
            'MAIL': '📨'
        }.get(log['action'], '•')
        
        message += f"{action_emoji} {admin_name}: {log['action']}"
        if log['target']:
            message += f" @{log['target']}"
        message += f"\n   🕐 {log['timestamp'][:16]}\n\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]]
    
    # Разбиваем на части если нужно
    if len(message) > 4000:
        parts = utils.split_message(message)
        for i, part in enumerate(parts):
            if i == 0:
                await query.edit_message_text(part, parse_mode="HTML", reply_markup=None)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=part,
                    parse_mode="HTML"
                )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="◀️ Назад в админку",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def admin_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Моя статистика как админа"""
    query = update.callback_query
    await query.answer()
    
    admin_id = update.effective_user.id
    admin_stats = database.get_admin_stats(admin_id)
    
    total_actions = sum(stat['count'] for stat in admin_stats) if admin_stats else 0
    
    # Получаем последние действия
    all_logs = database.get_admin_logs(50)
    my_logs = [log for log in all_logs if log['admin_id'] == admin_id][:10]
    
    message = (
        f"📈 <b>Твоя статистика</b>\n\n"
        f"👮 Админ ID: <code>{admin_id}</code>\n"
        f"📊 Всего действий: <b>{total_actions}</b>\n\n"
    )
    
    if admin_stats:
        message += "<b>По типам:</b>\n"
        for stat in admin_stats:
            emoji = '➕' if stat['action'] == 'ADD_SCAM' else '➖' if stat['action'] == 'REMOVE_SCAM' else '📨'
            message += f"{emoji} {stat['action']}: {stat['count']}\n"
    
    if my_logs:
        message += "\n<b>Последние действия:</b>\n"
        for log in my_logs[:5]:
            message += f"• {log['action']} @{log['target'] if log['target'] else ''} ({log['timestamp'][:16]})\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")]]
    
    await query.edit_message_text(
        message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в админку"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    await query.edit_message_text(
        f"👋 <b>Админ-панель</b>\n\n"
        f"🆔 Ваш ID: <code>{user.id}</code>\n"
        f"📊 Версия бота: {VERSION}\n\n"
        f"Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )

async def scamlist_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пагинации скам-списка"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.replace("scamlist_page_", ""))
    
    limit = 20
    offset = (page - 1) * limit
    
    scams = database.get_scam_list(limit, offset)
    total = database.get_scams_count()
    total_pages = (total + limit - 1) // limit
    
    if not scams:
        await query.edit_message_text(
            "📭 <b>Скам-база пуста</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_admin")
            ]])
        )
        return

    message = f"📋 <b>Скам-список (страница {page}/{total_pages})</b>\n"
    message += f"Всего в базе: {total}\n\n"
    
    for scam in scams:
        admin = database.get_user_by_id(scam['added_by'])
        admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {scam['added_by']}"
        
        message += f"• @{scam['username']}\n"
        message += f"  👮 Добавил: {admin_name}\n"
        message += f"  📅 {scam['added_at'][:16]}\n\n"
    
    # Кнопки навигации
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"scamlist_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"scamlist_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")])
    
    await query.edit_message_text(
        message,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== РАССЫЛКА ==========

# Храним состояние рассылки
user_mail_state = {}

async def admin_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать рассылку"""
    query = update.callback_query
    await query.answer()
    
    user_mail_state[update.effective_user.id] = "waiting_for_text"
    
    await query.edit_message_text(
        "📨 <b>Рассылка</b>\n\n"
        "Отправь мне текст для рассылки (можно с HTML-тегами):\n"
        "Или отправь /cancel для отмены",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="back_to_admin")
        ]])
    )

async def handle_mail_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для рассылки"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if user_mail_state.get(user_id) != "waiting_for_text":
        return

    mail_text = update.message.text
    
    if mail_text == "/cancel":
        user_mail_state.pop(user_id, None)
        await update.message.reply_text(
            "❌ Рассылка отменена",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
            ]])
        )
        return

    users = database.get_all_users(limit=1000)  # Получаем всех пользователей
    total_users = len(users)
    
    status_msg = await update.message.reply_text(
        f"📨 <b>Начинаю рассылку...</b>\n"
        f"Всего получателей: {total_users}\n\n"
        f"Прогресс: 0/{total_users}",
        parse_mode="HTML"
    )
    
    success = 0
    failed = 0
    failed_users = []
    
    for i, user in enumerate(users, 1):
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=mail_text,
                parse_mode="HTML"
            )
            success += 1
        except Exception as e:
            failed += 1
            failed_users.append(str(user['user_id']))
            logger.error(f"Ошибка отправки {user['user_id']}: {e}")
        
        # Обновляем прогресс каждые 10 сообщений
        if i % 10 == 0:
            await status_msg.edit_text(
                f"📨 <b>Рассылка...</b>\n\n"
                f"✅ Успешно: {success}\n"
                f"❌ Ошибок: {failed}\n"
                f"📊 Прогресс: {i}/{total_users}",
                parse_mode="HTML"
            )
    
    # Логируем рассылку
    database.log_admin_action(user_id, "MAIL", f"to {success} users")
    
    result_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Всего: {total_users}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}\n"
    )
    
    if failed_users:
        result_text += f"\n❌ Не удалось отправить {len(failed_users)} пользователям"
    
    keyboard = [[InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")]]
    
    await status_msg.edit_text(
        result_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    user_mail_state.pop(user_id, None)

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ДЛЯ АДМИНОВ ==========

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от админов"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    action = context.user_data.get('admin_action')
    
    if not action:
        return
    
    text = update.message.text.strip()
    
    if action == 'search_user':
        context.user_data.pop('admin_action', None)
        
        # Поиск по ID
        if text.isdigit():
            user = database.get_user_by_id(int(text))
            if user:
                scam_status = "🔴 В скаме" if user.get('username') and database.is_in_scam_db(user['username']) else "🟢 Чист"
                await update.message.reply_text(
                    f"🔍 <b>Найден пользователь:</b>\n\n"
                    f"👤 Имя: {user['first_name']}\n"
                    f"📛 Юзернейм: @{user['username'] if user['username'] else 'нет'}\n"
                    f"🆔 ID: <code>{user['user_id']}</code>\n"
                    f"📅 Последний вход: {utils.format_timestamp(user['last_seen'])}\n"
                    f"📊 Статус: {scam_status}",
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"❌ Пользователь с ID <code>{text}</code> не найден",
                    parse_mode="HTML"
                )
        
        # Поиск по username
        else:
            username = utils.extract_username(text)
            user = database.get_user_by_username(username)
            if user:
                scam_status = "🔴 В скаме" if database.is_in_scam_db(username) else "🟢 Чист"
                await update.message.reply_text(
                    f"🔍 <b>Найден пользователь:</b>\n\n"
                    f"👤 Имя: {user['first_name']}\n"
                    f"📛 Юзернейм: @{user['username']}\n"
                    f"🆔 ID: <code>{user['user_id']}</code>\n"
                    f"📅 Последний вход: {utils.format_timestamp(user['last_seen'])}\n"
                    f"📊 Статус: {scam_status}",
                    parse_mode="HTML"
                )
            else:
                # Ищем в скам-базе
                scams = database.search_scam(username)
                if scams:
                    scam = scams[0]
                    admin = database.get_user_by_id(scam['added_by'])
                    admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {scam['added_by']}"
                    
                    await update.message.reply_text(
                        f"🔴 <b>Найден в скам-базе!</b>\n\n"
                        f"📛 Юзернейм: @{scam['username']}\n"
                        f"👮 Добавил: {admin_name}\n"
                        f"📅 Добавлен: {scam['added_at'][:16]}",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Пользователь @{username} не найден",
                        parse_mode="HTML"
                    )
        
        await update.message.reply_text(
            "👋 Вернуться в админку: /start",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
            ]])
        )
    
    elif action == 'add_scam':
        context.user_data.pop('admin_action', None)
        username = utils.extract_username(text)
        
        if not utils.is_valid_username(username):
            await update.message.reply_text(
                "❌ Некорректный username",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
            return
        
        if database.add_to_scam_db(username, user_id):
            await update.message.reply_text(
                f"✅ @{username} добавлен в скам-базу!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
        else:
            await update.message.reply_text(
                f"⚠️ @{username} уже есть в базе",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
    
    elif action == 'remove_scam':
        context.user_data.pop('admin_action', None)
        username = utils.extract_username(text)
        
        if database.remove_from_scam_db(username, user_id):
            await update.message.reply_text(
                f"✅ @{username} удалён из скам-базы!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
        else:
            await update.message.reply_text(
                f"⚠️ @{username} не найден в базе",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
    
    elif action == 'search_scam':
        context.user_data.pop('admin_action', None)
        query = utils.extract_username(text)
        
        scams = database.search_scam(query)
        
        if not scams:
            await update.message.reply_text(
                f"🔎 По запросу '{query}' ничего не найдено",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
                ]])
            )
            return
        
        message = f"🔎 <b>Результаты поиска по '{query}':</b>\n\n"
        for scam in scams[:10]:
            admin = database.get_user_by_id(scam['added_by'])
            admin_name = f"@{admin['username']}" if admin and admin.get('username') else f"ID: {scam['added_by']}"
            message += f"• @{scam['username']} (добавил {admin_name}, {scam['added_at'][:16]})\n"
        
        if len(scams) > 10:
            message += f"\n...и ещё {len(scams) - 10}"
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 В админку", callback_data="back_to_admin")
            ]])
        )

# ========== ОБРАБОТКА НЕИЗВЕСТНЫХ КОМАНД ==========

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Неизвестная команда"""
    await update.message.reply_text(
        "❓ <b>Неизвестная команда</b>\n"
        "Используй /start для начала работы",
        parse_mode="HTML"
    )

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пустая кнопка"""
    query = update.callback_query
    await query.answer()

# ========== ЗАПУСК ==========

def main():
    """Запуск бота"""
    print("🚀 Запуск бота...")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search))
    
    # Админ-команды
    app.add_handler(CommandHandler("addscam", addscam))
    app.add_handler(CommandHandler("removescam", removescam))
    app.add_handler(CommandHandler("scamlist", scamlist))
    
    # Обработчики кнопок
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_search_user, pattern="^admin_search_user$"))
    app.add_handler(CallbackQueryHandler(admin_add_scam, pattern="^admin_add_scam$"))
    app.add_handler(CallbackQueryHandler(admin_remove_scam, pattern="^admin_remove_scam$"))
    app.add_handler(CallbackQueryHandler(admin_search_scam, pattern="^admin_search_scam$"))
    app.add_handler(CallbackQueryHandler(admin_mail, pattern="^admin_mail$"))
    app.add_handler(CallbackQueryHandler(admin_logs, pattern="^admin_logs$"))
    app.add_handler(CallbackQueryHandler(admin_my_stats, pattern="^admin_my_stats$"))
    app.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$"))
    app.add_handler(CallbackQueryHandler(scamlist_page, pattern="^scamlist_page_"))
    app.add_handler(CallbackQueryHandler(noop, pattern="^noop$"))
    
    # Обработчик текста для рассылки
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mail_text))
    
    # Обработчик текста для админ-действий
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))
    
    # Неизвестные команды
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("✅ Бот готов к работе!")
    print(f"👥 Админы: {ADMINS}")
    print(f"📊 Версия: {VERSION}")
    
    app.run_polling()

if __name__ == "__main__":
    main()