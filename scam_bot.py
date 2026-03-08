import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки
TOKEN = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
ADMIN_ID = 7040677455

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
        "added_by INTEGER, "
        "added_at TEXT"
        ")"
    )
    conn.commit()
    conn.close()

# Проверка наличия в базе
def is_in_scam_db(username: str) -> bool:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT 1 FROM scams WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Добавление в базу
def add_to_scam_db(username: str, admin_id: int) -> bool:
    if is_in_scam_db(username):
        return False
    conn = sqlite3.connect("scam_database.db")
    conn.execute(
        "INSERT INTO scams (username, added_by, added_at) VALUES (?, ?, ?)",
        (username, admin_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return True

# Удаление из базы
def remove_from_scam_db(username: str) -> bool:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("DELETE FROM scams WHERE username = ?", (username,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

# Получение списка
def get_scam_list() -> list:
    conn = sqlite3.connect("scam_database.db")
    cursor = conn.execute("SELECT username, added_at FROM scams ORDER BY added_at")
    results = cursor.fetchall()
    conn.close()
    return results

# Команда /start с новым приветствием
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Здравствуйте!</b> Я бот скам‑базы. Здесь вы найдёте актуальную информацию о мошеннических схемах и подозрительных ресурсах. "
        "Введите запрос, и я моментально предоставлю нужные данные. Будьте бдительны!\n\n"
        "<b>Команды:</b>\n"
        "/search @username — проверить"
    , parse_mode="HTML")

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

    if is_in_scam_db(username):
        await update.message.reply_text(
            f"🔴 @{username} <b>— найден в скам базе!</b>\n\n"
            "<b>Будьте осторожны и не доверяйте этой личности.</b> Рекомендуем избегать общения и не передавать личные данные.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"🟢 @{username} <b>— не найден в скам базе.</b>\n\n"
            "<b>Это означает, что на данный момент нет информации о мошеннической деятельности данного пользователя.</b> "
            "Однако всегда будьте внимательны и осторожны при общении с незнакомыми людьми!",
            parse_mode="HTML"
        )

# Команда /addscam (только для админа)
async def addscam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("Используйте: /addscam @username")
        return

    username = context.args[0].strip().lower()
    if not username.startswith("@") or len(username) < 3:
        await update.message.reply_text("Укажите @username")
        return

    username = username[1:]
    
    if add_to_scam_db(username, ADMIN_ID):
        await update.message.reply_text(f"✅ @{username} добавлен.")
    else:
        await update.message.reply_text(f"⚠️ @{username} уже в базе.")

# Команда /removescam (только для админа)
async def removescam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return

    if not context.args:
        await update.message.reply_text("Используйте: /removescam @username")
        return

    username = context.args[0].strip().lower()
    if not username.startswith("@") or len(username) < 3:
        await update.message.reply_text("Укажите @username")
        return

    username = username[1:]

    if remove_from_scam_db(username):
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

    message = f"Список ({len(scams)}) :\n"
    for username, timestamp in scams:
        message += f"• @{username} ({timestamp})\n"

    await update.message.reply_text(message)

# Обработка неизвестных команд
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Используй /start")

# Запуск бота
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("addscam", addscam))
    app.add_handler(CommandHandler("removescam", removescam))
    app.add_handler(CommandHandler("scamlist", scamlist))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()