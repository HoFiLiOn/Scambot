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

# ---------- ПОЛУЧЕНИЕ ПОСТОВ ----------
def get_channel_messages(limit=5):
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
                result.append({
                    'text': text[:400],
                    'date': date,
                    'link': link,
                    'id': msg_id
                })
            return result
        return []
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

# ---------- МОНИТОРИНГ ----------
last_post_id = None

async def monitor_channel(context):
    global last_post_id
    try:
        posts = get_channel_messages(limit=1)
        if posts:
            latest = posts[0]
            if last_post_id is None:
                last_post_id = latest['id']
                logger.info(f"Начат мониторинг, ID: {last_post_id}")
            elif latest['id'] != last_post_id:
                last_post_id = latest['id']
                await send_to_subscribers(context.bot, latest['text'], latest['link'])
                logger.info(f"Новый пост: {latest['link']}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

async def send_to_subscribers(bot, post_text, post_link):
    subscribers = get_all_subscribers()
    if not subscribers:
        return
    
    for user_id in subscribers:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🔔 НОВЫЙ ПОСТ!\n\n{post_text[:500]}\n\n{post_link}",
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            if "Forbidden" in str(e):
                remove_subscriber(user_id)
            logger.error(f"Ошибка {user_id}: {e}")

# ---------- КНОПКИ ----------
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ ПОДПИСАТЬСЯ", callback_data='subscribe')],
        [InlineKeyboardButton("❌ ОТПИСАТЬСЯ", callback_data='unsubscribe')],
        [InlineKeyboardButton("📜 ПОСЛЕДНИЕ 5", callback_data='last_5')],
        [InlineKeyboardButton("📜 ПОСЛЕДНИЕ 10", callback_data='last_10')],
        [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data='stats')],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- ОБРАБОТЧИКИ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👁 {BOT_NAME}\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"Я слежу за каналом Vexor cheats | News\n"
        f"и присылаю новые посты.\n\n"
        f"👇 ВЫБЕРИ ДЕЙСТВИЕ:",
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'subscribe':
        add_subscriber(user_id)
        await query.edit_message_text(
            f"✅ ПОДПИСАН!\n\n👀 Подписчиков: {len(get_all_subscribers())}",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data == 'unsubscribe':
        remove_subscriber(user_id)
        await query.edit_message_text("❌ ОТПИСАН", reply_markup=get_main_keyboard())
    
    elif query.data == 'stats':
        await query.edit_message_text(
            f"📊 СТАТИСТИКА\n\n👀 Подписчиков: {len(get_all_subscribers())}\n📢 Канал: Vexor cheats | News",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data in ['last_5', 'last_10']:
        n = 5 if query.data == 'last_5' else 10
        await query.edit_message_text(f"⏳ Загружаю {n} постов...")
        
        posts = get_channel_messages(limit=n)
        if posts:
            text = "\n\n".join([f"📌 {p['date'].strftime('%d.%m %H:%M')}\n{p['text']}\n{p['link']}" for p in posts])
            await query.edit_message_text(text, disable_web_page_preview=True)
        else:
            await query.edit_message_text("❌ Ошибка загрузки", reply_markup=get_main_keyboard())

# ---------- ЗАПУСК ----------
async def main():
    init_db()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем мониторинг через JobQueue (каждые 5 секунд)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(monitor_channel, interval=5, first=1)
    
    # Запускаем бота
    await application.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")