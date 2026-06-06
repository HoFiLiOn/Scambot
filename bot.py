import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===== КОНФИГ =====
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA'
ADMIN_ID =    # Твой Telegram ID (числом). Узнать через @userinfobot
# =================

subscribers = set()   # В реальности замени на SQLite или файл

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Подписаться", callback_data='subscribe')],
        [InlineKeyboardButton("❌ Отписаться", callback_data='unsubscribe')]
    ]
    await update.message.reply_text(
        "👋 Бот-уведомитель канала @vexor_cheat\n"
        "Нажимай кнопки, чтобы получать новые посты.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribers.add(user_id)
    await update.message.reply_text("✅ Ты подписан на уведомления!")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    subscribers.discard(user_id)
    await update.message.reply_text("❌ Ты отписался.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == 'subscribe':
        subscribers.add(user_id)
        await query.edit_message_text("✅ Подписка оформлена.")
    elif query.data == 'unsubscribe':
        subscribers.discard(user_id)
        await query.edit_message_text("❌ Подписка отменена.")

async def broadcast_to_subscribers(text: str):
    """Вызывается извне (например, юзерботом) для массовой рассылки"""
    for uid in subscribers:
        try:
            await application.bot.send_message(chat_id=uid, text=text)
        except:
            pass

def main():
    global application
    app = Application.builder().token(BOT_TOKEN).build()
    application = app
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Бот запущен и ждёт команды.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()