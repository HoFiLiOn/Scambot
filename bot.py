import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

# ========== ТВОИ ДАННЫЕ ==========
API_ID = 23265830               # Твой api_id
API_HASH = '64ba5bd3a3826ab7e4b9fa9cfa11239'   # Твой api_hash
PHONE = '+79087358155'          # ЗАМЕНИ на номер фейкового аккаунта

# Тестовый канал (твой, для проверки)
SOURCE_CHANNEL = '@Twst_hof'

# Куда пересылать ('me' — себе в избранное)
DEST = 'me'
# =================================

client = TelegramClient('my_working_session', API_ID, API_HASH)

async def main():
    await client.start(PHONE)
    print('[✔] Юзербот авторизован')

    # Вступаем в канал (если ещё не вступили)
    try:
        await client(JoinChannelRequest(SOURCE_CHANNEL))
        print(f'[✔] Подписались на {SOURCE_CHANNEL}')
    except Exception as e:
        print(f'[!] Уже подписаны или ошибка: {e}')

    # Сущность канала-источника
    source = await client.get_entity(SOURCE_CHANNEL)
    
    # Сущность получателя
    if DEST == 'me':
        dest = await client.get_me()
        print('[•] Пересылаю в "Избранное"')
    else:
        dest = await client.get_entity(DEST)

    # Слушаем новые сообщения в канале
    @client.on(events.NewMessage(chats=source))
    async def forward_to_dest(event):
        try:
            await client.send_message(dest, event.message)
            text = event.raw_text[:50] if event.raw_text else '[медиа/файл]'
            print(f'[→] Переслано: {text}')
        except Exception as e:
            print(f'[!] Ошибка пересылки: {e}')

    print(f'[•] Слежу за каналом {SOURCE_CHANNEL}. Жду сообщений...')
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())