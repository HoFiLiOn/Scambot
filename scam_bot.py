import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ========== НАСТРОЙКИ (сам поменяй если чё) ==========
ТОКЕН = "8597361234:AAH6H24ZM2DJdt4Mxv9PH1aeNLu39Mt_gok"
АДМИНЫ = [7496116016, 7040677455]  # Владелец и ты

# ========== БАЗА ДАННЫХ ==========
def получить_бд():
    conn = sqlite3.connect("база.db")
    conn.row_factory = sqlite3.Row
    return conn

def создать_таблицы():
    conn = получить_бд()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS скам (
            юзернейм TEXT PRIMARY KEY,
            добавил INTEGER,
            когда TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS юзеры (
            айди INTEGER PRIMARY KEY,
            юзернейм TEXT,
            имя TEXT,
            последний_раз TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ База создана!")

создать_таблицы()

# ========== ПРОВЕРКА НА АДМИНА ==========
def админ_ли(айди):
    return айди in АДМИНЫ

# ========== СОХРАНЕНИЕ ЮЗЕРА ==========
def сохранить_юзера(юзер):
    conn = получить_бд()
    conn.execute("""
        INSERT OR REPLACE INTO юзеры (айди, юзернейм, имя, последний_раз)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (юзер.id, юзер.username, юзер.first_name))
    conn.commit()
    conn.close()

# ========== ПРОВЕРКА В СКАМЕ ==========
def в_скаме(юзернейм):
    юзернейм = юзернейм.lower().replace("@", "")
    conn = получить_бд()
    курсор = conn.execute("SELECT 1 FROM скам WHERE юзернейм = ?", (юзернейм,))
    есть = курсор.fetchone() is not None
    conn.close()
    return есть

# ========== ДОБАВИТЬ В СКАМ ==========
def добавить_в_скам(юзернейм, айди_админа):
    юзернейм = юзернейм.lower().replace("@", "")
    if в_скаме(юзернейм):
        return False
    conn = получить_бд()
    conn.execute(
        "INSERT INTO скам (юзернейм, добавил) VALUES (?, ?)",
        (юзернейм, айди_админа)
    )
    conn.commit()
    conn.close()
    return True

# ========== УДАЛИТЬ ИЗ СКАМА ==========
def удалить_из_скама(юзернейм, айди_админа):
    юзернейм = юзернейм.lower().replace("@", "")
    conn = получить_бд()
    курсор = conn.execute("DELETE FROM скам WHERE юзернейм = ?", (юзернейм,))
    удалено = курсор.rowcount > 0
    conn.commit()
    conn.close()
    return удалено

# ========== ВСЕ СКАМЕРЫ ==========
def все_скамеры():
    conn = получить_бд()
    курсор = conn.execute("SELECT юзернейм, когда FROM скам ORDER BY когда DESC")
    результаты = курсор.fetchall()
    conn.close()
    return [dict(строка) for строка in результаты]

# ========== НАЙТИ ЮЗЕРА ПО АЙДИ ==========
def найти_юзера_по_айди(айди):
    conn = получить_бд()
    курсор = conn.execute("SELECT * FROM юзеры WHERE айди = ?", (айди,))
    юзер = курсор.fetchone()
    conn.close()
    return dict(юзер) if юзер else None

# ========== ВСЕ ЮЗЕРЫ ==========
def все_юзеры(лимит=10):
    conn = получить_бд()
    курсор = conn.execute("""
        SELECT айди, юзернейм, имя, последний_раз 
        FROM юзеры 
        ORDER BY последний_раз DESC 
        LIMIT ?
    """, (лимит,))
    результаты = курсор.fetchall()
    conn.close()
    return [dict(строка) for строка in результаты]

# ========== СКОЛЬКО ЮЗЕРОВ ==========
def сколько_юзеров():
    conn = получить_бд()
    курсор = conn.execute("SELECT COUNT(*) FROM юзеры")
    количество = курсор.fetchone()[0]
    conn.close()
    return количество

# ========== СКОЛЬКО В СКАМЕ ==========
def сколько_в_скаме():
    conn = получить_бд()
    курсор = conn.execute("SELECT COUNT(*) FROM скам")
    количество = курсор.fetchone()[0]
    conn.close()
    return количество

# ========== КНОПКИ АДМИНКИ ==========
def кнопки_админки():
    клавиатура = [
        [InlineKeyboardButton("📊 Статистика", callback_data="стата")],
        [InlineKeyboardButton("👥 Юзеры", callback_data="юзеры")],
        [InlineKeyboardButton("📋 Скам-список", callback_data="скамлист")],
        [InlineKeyboardButton("➕ Добавить в скам", callback_data="добавить")],
        [InlineKeyboardButton("➖ Удалить из скам", callback_data="удалить")],
    ]
    return InlineKeyboardMarkup(клавиатура)

# ========== КОМАНДА СТАРТ ==========
async def старт(обновление, контекст):
    юзер = обновление.effective_user
    сохранить_юзера(юзер)
    
    if админ_ли(юзер.id):
        await обновление.message.reply_text(
            f"👋 Привет, админ!\nТвой ID: {юзер.id}\n\nВыбирай:",
            reply_markup=кнопки_админки()
        )
    else:
        await обновление.message.reply_text(
            "👋 Привет!\n\n/search @username - проверить чела\n/search 123456789 - проверить по ID"
        )

# ========== КОМАНДА ПОИСК ==========
async def поиск(обновление, контекст):
    юзер = обновление.effective_user
    сохранить_юзера(юзер)
    
    if not контекст.args:
        await обновление.message.reply_text("Используй: /search @username или /search 123456789")
        return

    запрос = контекст.args[0].strip()
    
    # Если это ID
    if запрос.isdigit():
        айди = int(запрос)
        найден = найти_юзера_по_айди(айди)
        
        if найден:
            if найден.get('юзернейм') and в_скаме(найден['юзернейм']):
                вердикт = "🔴 В СКАМЕ!"
            else:
                вердикт = "🟢 Чист"
            
            await обновление.message.reply_text(
                f"Нашел по ID {айди}:\n"
                f"Имя: {найден['имя']}\n"
                f"Юзернейм: @{найден['юзернейм'] if найден['юзернейм'] else 'нет'}\n"
                f"Статус: {вердикт}"
            )
        else:
            await обновление.message.reply_text(f"Юзер с ID {айди} еще не заходил")
        return
    
    # Если это юзернейм
    юзернейм = запрос.lower().replace("@", "")
    
    if в_скаме(юзернейм):
        await обновление.message.reply_text(
            f"🔴 @{юзернейм} В СКАМ-БАЗЕ!\n"
            f"МОШЕННИК! Не общайся!"
        )
    else:
        await обновление.message.reply_text(
            f"🟢 @{юзернейм} чист\n"
            f"Но будь осторожен!"
        )

# ========== ДОБАВИТЬ В СКАМ ==========
async def добавить_скам(обновление, контекст):
    if not админ_ли(обновление.effective_user.id):
        return

    if not контекст.args:
        await обновление.message.reply_text("Используй: /addscam @username")
        return

    юзернейм = контекст.args[0].lower().replace("@", "")
    
    if добавить_в_скам(юзернейм, обновление.effective_user.id):
        await обновление.message.reply_text(f"✅ @{юзернейм} добавлен в скам!")
    else:
        await обновление.message.reply_text(f"⚠️ @{юзернейм} уже в базе")

# ========== УДАЛИТЬ ИЗ СКАМА ==========
async def удалить_скам(обновление, контекст):
    if not админ_ли(обновление.effective_user.id):
        return

    if not контекст.args:
        await обновление.message.reply_text("Используй: /removescam @username")
        return

    юзернейм = контекст.args[0].lower().replace("@", "")
    
    if удалить_из_скама(юзернейм, обновление.effective_user.id):
        await обновление.message.reply_text(f"✅ @{юзернейм} удален из скам!")
    else:
        await обновление.message.reply_text(f"⚠️ @{юзернейм} не найден")

# ========== СПИСОК СКАМЕРОВ ==========
async function скамлист(обновление, контекст):
    if not админ_ли(обновление.effective_user.id):
        return

    скамеры = все_скамеры()
    
    if not скамеры:
        await обновление.message.reply_text("Скам-база пуста")
        return

    текст = f"📋 Всего в скаме: {len(скамеры)}\n\n"
    for с in скамеры[:10]:
        текст += f"• @{с['юзернейм']} ({с['когда'][:16]})\n"
    
    await обновление.message.reply_text(текст)

# ========== ОБРАБОТКА КНОПОК ==========
async def кнопки(обновление, контекст):
    запрос = обновление.callback_query
    await запрос.answer()
    
    if запрос.data == "стата":
        юзеры = сколько_юзеров()
        скамы = сколько_в_скаме()
        
        await запрос.edit_message_text(
            f"📊 Статистика:\n"
            f"👥 Юзеров: {юзеры}\n"
            f"🔴 В скаме: {скамы}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="назад")
            ]])
        )
    
    elif запрос.data == "юзеры":
        юзеры = все_юзеры(10)
        текст = "👥 Последние юзеры:\n\n"
        for ю in юзеры:
            текст += f"• {ю['имя']} (@{ю['юзернейм'] if ю['юзернейм'] else 'нет'})\n"
        
        await запрос.edit_message_text(
            текст,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="назад")
            ]])
        )
    
    elif запрос.data == "скамлист":
        скамеры = все_скамеры()
        if not скамеры:
            await запрос.edit_message_text(
                "Скам-база пуста",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад", callback_data="назад")
                ]])
            )
            return
        
        текст = f"📋 Скам-список:\n\n"
        for с in скамеры[:10]:
            текст += f"• @{с['юзернейм']}\n"
        
        await запрос.edit_message_text(
            текст,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="назад")
            ]])
        )
    
    elif запрос.data == "добавить":
        await запрос.edit_message_text(
            "➕ Отправь @username кого добавить в скам",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="назад")
            ]])
        )
        контекст.user_data['ждем'] = 'добавить'
    
    elif запрос.data == "удалить":
        await запрос.edit_message_text(
            "➖ Отправь @username кого удалить из скам",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="назад")
            ]])
        )
        контекст.user_data['ждем'] = 'удалить'
    
    elif запрос.data == "назад":
        await запрос.edit_message_text(
            "👋 Админ-панель\n\nВыбирай:",
            reply_markup=кнопки_админки()
        )

# ========== ЧТО ПИШУТ АДМИНЫ ==========
async function текст_от_админа(обновление, контекст):
    айди = обновление.effective_user.id
    
    if not админ_ли(айди):
        return
    
    if 'ждем' not in контекст.user_data:
        return
    
    действие = контекст.user_data['ждем']
    текст = обновление.message.text.strip()
    юзернейм = текст.lower().replace("@", "")
    
    if действие == 'добавить':
        if добавить_в_скам(юзернейм, айди):
            await обновление.message.reply_text(f"✅ @{юзернейм} добавлен!")
        else:
            await обновление.message.reply_text(f"⚠️ @{юзернейм} уже в базе")
    
    elif действие == 'удалить':
        if удалить_из_скама(юзернейм, айди):
            await обновление.message.reply_text(f"✅ @{юзернейм} удален!")
        else:
            await обновление.message.reply_text(f"⚠️ @{юзернейм} не найден")
    
    контекст.user_data.pop('ждем', None)
    await обновление.message.reply_text(
        "Возвращайся в админку /start",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 В админку", callback_data="назад")
        ]])
    )

# ========== ЗАПУСК ==========
def main():
    print("🚀 Бот запускается...")
    
    app = Application.builder().token(ТОКЕН).build()

    app.add_handler(CommandHandler("start", старт))
    app.add_handler(CommandHandler("search", поиск))
    app.add_handler(CommandHandler("addscam", добавить_скам))
    app.add_handler(CommandHandler("removescam", удалить_скам))
    app.add_handler(CommandHandler("scamlist", скамлист))
    
    app.add_handler(CallbackQueryHandler(кнопки))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, текст_от_админа))

    print("✅ Бот работает!")
    print(f"👥 Админы: {АДМИНЫ}")
    
    app.run_polling()

if __name__ == "__main__":
    main()