import asyncio
from telethon import TelegramClient, events

# ===== Данные епт =====
API_ID = 23265830                
API_HASH = '64ba5bd3a3826ab7e4b9fa9cfa11239'
PHONE = '79966598339'           
# ============================================

CHANNEL_TO_WATCH = '@TWSA_HOF'  
BOT_TOKEN = '8891687206:AAHUcgCDsiZr5YqQyx4kWPsMWfmw8IttikA' 

client = TelegramClient('monitor_session', API_ID, API_HASH)

async def send_to_bot(message_text):
    """Отправляем сообщение в бота (через API)"""
    from telethon.tl.functions.messages import SendMessageRequest
    await client(SendMessageRequest(
        peer='me',   # Можно отправить самому себе, а бот потом перешлёт
        message=message_text
    ))

@client.on(events.NewMessage(chats=CHANNEL_TO_WATCH))
async def new_post_handler(event):
    text = event.raw_text or '[Медиа / Файл / Фото]'
    await send_to_bot(f"🔔 Новый пост в канале {CHANNEL_TO_WATCH}:\n\n{text}")

async def main():
    await client.start(PHONE)
    print("✅ Юзербот запущен и мониторит канал.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())