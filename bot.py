import asyncio
import sqlite3
import logging
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA'
BOT_NAME = "Vexor Observer"
ADMIN_ID = 79966598339  # ТВОЙ ID
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

# ---------- КНОПКИ ----------
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ ПОДПИСАТЬСЯ", callback_data='subscribe')],
        [InlineKeyboardButton("❌ ОТПИСАТЬСЯ", callback_data='unsubscribe')],
        [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data='stats')],
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👁 {BOT_NAME}\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"Подпишись, чтобы получать новые посты из Vexor cheats | News\n\n"
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
            f"📊 СТАТИСТИКА\n\n👀 Подписчиков: {len(get_all_subscribers())}",
            reply_markup=get_main_keyboard()
        )

# ---------- КОМАНДЫ АДМИНА ----------
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить пост всем подписчикам - /post текст"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа")
        return
    
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("❌ Используй: /post текст поста")
        return
    
    subscribers = get_all_subscribers()
    if not subscribers:
        await update.message.reply_text("Нет подписчиков")
        return
    
    await update.message.reply_text(f"📤 Рассылаю {len(subscribers)} подписчикам...")
    
    success = 0
    for user_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🔔 НОВЫЙ ПОСТ ИЗ КАНАЛА!\n\n{text}"
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            if "Forbidden" in str(e):
                remove_subscriber(user_id)
    
    await update.message.reply_text(f"✅ Отправлено: {success}/{len(subscribers)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить любое сообщение - /broadcast текст"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Только для админа")
        return
    
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("❌ Используй: /broadcast текст")
        return
    
    subscribers = get_all_subscribers()
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Ошибка {user_id}: {e}")
    
    await update.message.reply_text("✅ Готово")

# ---------- ЗАПУСК ----------
async def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler('post', post))
    application.add_handler(CommandHandler('broadcast', broadcast))
    
    logger.info("✅ Бот запущен! Используй /post текст для рассылки")
    
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())