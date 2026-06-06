import asyncio
import sqlite3
import logging
import sys
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA'
SOURCE_CHANNEL = '@TWSA_HOF'
BOT_NAME = "Vexor Observer"
API_URL = f"https://tg.i-c-a.su/json/{SOURCE_CHANNEL}"
# ==================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('subscribers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()
    logger.info("База данных готова")

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
    return len(get_all_subscribers())

# ---------- ПОЛУЧЕНИЕ ПОСТОВ ----------
last_post_id = None

def get_latest_post():
    global last_post_id
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            messages = data.get('messages', [])
            if messages:
                latest = messages[0]
                current_id = latest.get('id')
                text = latest.get('text', 'Новый пост')
                if isinstance(text, list):
                    text = ' '.join(str(item) for item in text)
                link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{current_id}"
                
                if last_post_id is None:
                    last_post_id = current_id
                    return None
                elif current_id != last_post_id:
                    last_post_id = current_id
                    return {'text': text[:500], 'link': link}
        return None
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def get_last_posts(limit=5):
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            messages = data.get('messages', [])
            result = []
            for msg in messages[:limit]:
                text = msg.get('text', '📷 Медиа')
                if isinstance(text, list):
                    text = ' '.join(str(item) for item in text)
                date = datetime.fromtimestamp(msg.get('date', 0))
                msg_id = msg.get('id')
                link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{msg_id}"
                result.append(f"📌 <b>{date.strftime('%d.%m %H:%M')}</b>\n{text[:300]}\n<a href='{link}'>🔗 Читать</a>")
            return result
        return []
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

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

# ---------- КОМАНДЫ БОТА ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"<b>👁 {BOT_NAME}</b>\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"Я слежу за каналом <b>Vexor cheats | News</b>\n"
        f"и присылаю новые посты.\n\n"
        f"👇 <b>ВЫБЕРИ ДЕЙСТВИЕ:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_subscriber(user_id)
    await update.message.reply_text(
        f"<b>✅ ПОДПИСАН!</b>\n\n👀 Подписчиков: {get_subscriber_count()}",
        parse_mode='HTML'
    )

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    remove_subscriber(user_id)
    await update.message.reply_text(
        "<b>❌ ОТПИСАН</b>",
        parse_mode='HTML'
    )

async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = 5
    if context.args and context.args[0].isdigit():
        n = min(int(context.args[0]), 20)
    
    msg = await update.message.reply_text(f"⏳ Загружаю {n} постов...")
    posts = get_last_posts(n)
    if posts:
        text = "\n\n".join(posts)
        await msg.edit_text(text, parse_mode='HTML', disable_web_page_preview=True)
    else:
        await msg.edit_text("❌ Ошибка загрузки")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>📊 СТАТИСТИКА</b>\n\n👀 Подписчиков: {get_subscriber_count()}\n📢 Канал: Vexor cheats | News",
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'subscribe':
        add_subscriber(user_id)
        await query.edit_message_text(
            f"<b>✅ ПОДПИСАН!</b>\n\n👀 Подписчиков: {get_subscriber_count()}",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data == 'unsubscribe':
        remove_subscriber(user_id)
        await query.edit_message_text(
            "<b>❌ ОТПИСАН</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data == 'stats':
        await query.edit_message_text(
            f"<b>📊 СТАТИСТИКА</b>\n\n👀 Подписчиков: {get_subscriber_count()}\n📢 Канал: Vexor cheats | News",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data in ['last_5', 'last_10']:
        n = 5 if query.data == 'last_5' else 10
        await query.edit_message_text(f"⏳ Загружаю {n} постов...")
        
        posts = get_last_posts(n)
        if posts:
            text = "\n\n".join(posts)
            await query.edit_message_text(text, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await query.edit_message_text("❌ Ошибка загрузки", reply_markup=get_main_keyboard())

# ---------- МОНИТОРИНГ ----------
async def monitor_channel(context):
    post = get_latest_post()
    if post:
        subscribers = get_all_subscribers()
        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"<b>🔔 НОВЫЙ ПОСТ!</b>\n\n{post['text']}\n\n<a href='{post['link']}'>🔗 Открыть</a>",
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                if "Forbidden" in str(e):
                    remove_subscriber(user_id)
                logger.error(f"Ошибка {user_id}: {e}")

# ---------- ЗАПУСК ----------
async def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('subscribe', subscribe_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))
    application.add_handler(CommandHandler('last', last_command))
    application.add_handler(CommandHandler('stats', stats_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем мониторинг
    async def monitor_wrapper():
        while True:
            await monitor_channel(application)
            await asyncio.sleep(5)
    
    asyncio.create_task(monitor_wrapper())
    
    logger.info("✅ Бот запущен! Доступные команды: /start, /subscribe, /unsubscribe, /last N, /stats")
    await application.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")