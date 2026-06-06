import asyncio
import sqlite3
import logging

from telethon import TelegramClient, events
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
API_ID = 23265830
API_HASH = '64ba5bd3a3826ab7e4b9fa9cfa11239'
PHONE = '+79966598339'
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA'

SOURCE_CHANNEL = '@TWSA_HOF'  # Канал за которым следим
# ==================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_subscriber(user_id):
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_subscriber(user_id):
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscribers WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM subscribers')
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_subscriber_count():
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM subscribers')
    count = c.fetchone()[0]
    conn.close()
    return count

# ---------- ЦВЕТНЫЕ КНОПКИ ----------
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("✅ ПОДПИСАТЬСЯ", callback_data='subscribe', style='success'),
            InlineKeyboardButton("❌ ОТПИСАТЬСЯ", callback_data='unsubscribe', style='danger'),
        ],
        [
            InlineKeyboardButton("📜 ПОСЛЕДНИЕ 5", callback_data='last_5', style='primary'),
            InlineKeyboardButton("📜 ПОСЛЕДНИЕ 10", callback_data='last_10', style='primary'),
        ],
        [
            InlineKeyboardButton("📊 СТАТИСТИКА", callback_data='stats', style='primary'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- БОТ КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"<b>👁 СКРЫТЫЙ НАБЛЮДАТЕЛЬ</b>\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"Я буду незаметно следить за каналом <b>{SOURCE_CHANNEL}</b>\n"
        f"и присылать тебе все новые посты.\n\n"
        f"Никто не узнает, что ты следишь 😉\n\n"
        f"👇 <b>ВЫБЕРИ ДЕЙСТВИЕ:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # ПОДПИСКА
    if query.data == 'subscribe':
        add_subscriber(user_id)
        await query.edit_message_text(
            f"<b>✅ ТЫ В ИГРЕ</b>\n\n"
            f"Теперь все новые посты из <b>{SOURCE_CHANNEL}</b>\n"
            f"будут приходить сюда.\n\n"
            f👀 Наблюдателей: <b>{get_subscriber_count()}</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    # ОТПИСКА
    elif query.data == 'unsubscribe':
        remove_subscriber(user_id)
        await query.edit_message_text(
            f"<b>❌ ТЫ ВЫШЕЛ ИЗ ТЕНИ</b>\n\n"
            f"Посты больше приходить не будут.\n"
            f"Чтобы вернуться - жми зеленую кнопку.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    # СТАТИСТИКА
    elif query.data == 'stats':
        await query.edit_message_text(
            f"<b>📊 СТАТИСТИКА</b>\n\n"
            f"👀 Активных наблюдателей: <b>{get_subscriber_count()}</b>\n"
            f"📢 Отслеживаемый канал: <b>{SOURCE_CHANNEL}</b>\n"
            f"🕐 Обновления: моментальные\n\n"
            f"<i>Ты один из тех, кто следит незаметно...</i>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    # ПОСЛЕДНИЕ ПОСТЫ
    elif query.data in ['last_5', 'last_10']:
        n = 5 if query.data == 'last_5' else 10
        await query.edit_message_text(f"<i>⏳ Загружаю последние {n} постов...</i>", parse_mode='HTML')
        
        global userbot_client
        if not userbot_client or not userbot_client.is_connected():
            await query.edit_message_text(
                f"<b>❌ ОШИБКА</b>\n\nСервис временно недоступен",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        try:
            channel = await userbot_client.get_entity(SOURCE_CHANNEL)
            messages = []