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

SOURCE_CHANNEL = '@TWSA_HOF'
BOT_NAME = "Vexor Observer"
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
        f"<b>👁 {BOT_NAME}</b>\n\n"
        f"Привет, {user.first_name}!\n\n"
        f"Я незаметно слежу за каналом <b>Vexor cheats | News</b>\n"
        f"и присылаю все новые посты подписчикам.\n\n"
        f"Никто не узнает, что ты следишь 😉\n\n"
        f"👇 <b>ВЫБЕРИ ДЕЙСТВИЕ:</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'subscribe':
        add_subscriber(user_id)
        await query.edit_message_text(
            f"<b>✅ ТЫ ПОДПИСАН</b>\n\n"
            f"Теперь все новые посты из <b>Vexor cheats | News</b>\n"
            f"будут приходить сюда.\n\n"
            f"👀 Наблюдателей: <b>{get_subscriber_count()}</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data == 'unsubscribe':
        remove_subscriber(user_id)
        await query.edit_message_text(
            f"<b>❌ ТЫ ОТПИСАН</b>\n\n"
            f"Посты больше приходить не будут.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data == 'stats':
        await query.edit_message_text(
            f"<b>📊 СТАТИСТИКА</b>\n\n"
            f"👀 Наблюдателей: <b>{get_subscriber_count()}</b>\n"
            f"📢 Канал: <b>Vexor cheats | News</b>\n"
            f"🕐 Обновления: моментальные",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif query.data in ['last_5', 'last_10']:
        n = 5 if query.data == 'last_5' else 10
        await query.edit_message_text(f"<i>⏳ Загружаю {n} последних постов...</i>", parse_mode='HTML')
        
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
            async for msg in userbot_client.iter_messages(channel, limit=n):
                text = msg.text if msg.text else "📷 Медиа"
                if len(text) > 400:
                    text = text[:400] + "..."
                link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{msg.id}"
                messages.append(
                    f"<b>📌 {msg.date.strftime('%d.%m %H:%M')}</b>\n"
                    f"{text}\n"
                    f"<a href='{link}'>🔗 Читать</a>\n"
                )
            
            if messages:
                await query.edit_message_text(
                    "\n\n".join(messages[::-1]),
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                await query.message.reply_text("👇 Чтобы вернуться в меню, нажми /start", reply_markup=get_main_keyboard())
            else:
                await query.edit_message_text(
                    f"<i>Нет постов в канале</i>",
                    reply_markup=get_main_keyboard(),
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await query.edit_message_text(
                f"<b>❌ ОШИБКА</b>\n\nНе удалось загрузить посты",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )

# ---------- РАССЫЛКА ПОДПИСЧИКАМ ----------
async def send_to_subscribers(bot_app: Application, post_text: str, post_link: str):
    subscribers = get_all_subscribers()
    if not subscribers:
        return
    
    success = 0
    for user_id in subscribers:
        try:
            await bot_app.bot.send_message(
                chat_id=user_id,
                text=f"<b>🔔 НОВЫЙ ПОСТ В КАНАЛЕ!</b>\n\n{post_text[:500]}\n\n<a href='{post_link}'>🔗 Открыть</a>",
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            if "Forbidden" in str(e):
                remove_subscriber(user_id)
            logger.error(f"Ошибка отправки {user_id}: {e}")
    
    logger.info(f"Рассылка: {success}/{len(subscribers)}")

# ---------- ЮЗЕРБОТ ----------
userbot_client = TelegramClient('userbot_session', API_ID, API_HASH)

async def run_userbot():
    await userbot_client.start(PHONE)
    logger.info(f"✅ Юзербот запущен, слежу за {SOURCE_CHANNEL}")
    
    bot_entity = await userbot_client.get_entity(f"@{BOT_TOKEN.split(':')[0]}")
    
    @userbot_client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def on_new_post(event):
        try:
            post_text = event.message.text if event.message.text else "📷 Новый пост"
            post_link = f"https://t.me/{SOURCE_CHANNEL[1:]}/{event.message.id}"
            
            await userbot_client.send_message(
                bot_entity,
                f"/forward_post\n{post_text}\n---\n{post_link}"
            )
            logger.info(f"Новый пост отправлен боту")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
    
    await userbot_client.run_until_disconnected()

# ---------- ПРИЕМ ПОСТОВ ОТ ЮЗЕРБОТА ----------
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    if text.startswith('/forward_post'):
        parts = text.split('\n---\n')
        if len(parts) == 2:
            post_text = parts[0].replace('/forward_post\n', '')
            post_link = parts[1]
            await send_to_subscribers(context.bot, post_text, post_link)

# ---------- ЗАПУСК ----------
async def main():
    init_db()
    
    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CommandHandler('forward_post', handle_forward))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    
    await asyncio.gather(
        bot_app.run_polling(),
        run_userbot()
    )

if __name__ == '__main__':
    asyncio.run(main())