import asyncio
import sqlite3
import logging
import sys
import feedparser
import requests
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from bs4 import BeautifulSoup

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA'
SOURCE_CHANNEL = '@TWSA_HOF'  # Для RSS нужно преобразовать
BOT_NAME = "Vexor Observer"

# Каналы Telegram редко имеют RSS, но есть костыль через tgstat или t.me/rss/
# ИЛИ используем публичный API: https://api.telegram.org/bot{token}/getUpdates
# Но для чтения канала без API_ID - почти невозможно.

# Альтернатива: парсинг через tg-channel-parser (публичный)
# ==========================================================

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

# ---------- ПАРСИНГ КАНАЛА ЧЕРЕЗ ПУБЛИЧНЫЙ ПРОКСИ ----------
# Некоторые сервисы предоставляют RSS для Telegram каналов
# Например: https://tg.i-c-a.su/json/@TWSA_HOF
# Или: https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1

RSS_URL = f"https://tg.i-c-a.su/json/@TWSA_HOF"  # Публичный API без авторизации

async def get_last_posts(limit=5):
    try:
        response = requests.get(RSS_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = []
            for msg in data.get('messages', [])[:limit]:
                text = msg.get('text', 'Нет текста')
                date = datetime.fromtimestamp(msg.get('date', 0))
                link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{msg.get('id')}"
                posts.append({
                    'text': text[:400],
                    'date': date,
                    'link': link
                })
            return posts
        else:
            logger.error(f"Ошибка API: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
        return []

async def monitor_channel(bot_app: Application):
    """Мониторинг новых постов через публичный API"""
    last_post_id = None
    
    while True:
        try:
            response = requests.get(RSS_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                
                if messages:
                    latest = messages[0]
                    current_id = latest.get('id')
                    
                    if last_post_id is None:
                        last_post_id = current_id
                        logger.info(f"Начат мониторинг, последний ID: {last_post_id}")
                    elif current_id != last_post_id:
                        # Новый пост!
                        last_post_id = current_id
                        text = latest.get('text', 'Новый пост')
                        link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{current_id}"
                        await send_to_subscribers(bot_app, text, link)
                        logger.info(f"Новый пост отправлен подписчикам: {link}")
            
            await asyncio.sleep(5)  # Проверяем каждые 5 секунд
            
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            await asyncio.sleep(10)

# ---------- РАССЫЛКА ----------
async def send_to_subscribers(bot_app: Application, post_text: str, post_link: str):
    subscribers = get_all_subscribers()
    if not subscribers:
        return
    
    for user_id in subscribers:
        try:
            await bot_app.bot.send_message(
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
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👁 {BOT_NAME} (BETA - БЕЗ API)\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"⚠️ Экспериментальная версия без API ID/Hash\n"
        f"Работает через публичный парсинг канала.\n\n"
        f"Может работать с задержкой и нестабильно.\n\n"
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
            f"✅ ТЫ ПОДПИСАН (ЭКСПЕРИМЕНТ)\n\n"
            f"Попробуем следить без API...\n\n"
            f"👀 Наблюдателей: {len(get_all_subscribers())}",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data == 'unsubscribe':
        remove_subscriber(user_id)
        await query.edit_message_text(
            f"❌ ТЫ ОТПИСАН",
            reply_markup=get_main_keyboard()
        )
    
    elif query.data == 'last_5':
        await query.edit_message_text("⏳ Загружаю последние 5 постов...")
        
        posts = await get_last_posts(5)
        if posts:
            text = "\n\n".join([f"📌 {p['date'].strftime('%d.%m %H:%M')}\n{p['text']}\n{p['link']}" for p in posts])
            await query.edit_message_text(text, disable_web_page_preview=True)
        else:
            await query.edit_message_text("❌ Не удалось загрузить посты")

# ---------- ЗАПУСК ----------
async def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("✅ Бот запущен (ЭКСПЕРИМЕНТАЛЬНАЯ ВЕРСИЯ БЕЗ API)")
    
    # Запускаем мониторинг
    monitor_task = asyncio.create_task(monitor_channel(application))
    
    await monitor_task

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")