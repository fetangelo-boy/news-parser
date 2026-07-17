#!/usr/bin/env python3
import asyncio
from telethon import TelegramClient
from telethon.errors import InviteHashExpiredError, InviteHashInvalidError

API_ID = 37689624
API_HASH = '99a3c171f2474762219cb2340e512524'
INVITE_HASH = '-_V19XANAdFkOWFi'

async def main():
    client = TelegramClient('parser_session', API_ID, API_HASH)
    await client.start()
    print('✓ Подключено к Telegram')

    # Пробуем получить канал по invite-ссылке
    invite_link = f'https://t.me/+{INVITE_HASH}'
    print(f'🔍 Проверяем ссылку: {invite_link}')
    
    try:
        # Метод 1: get_entity
        entity = await client.get_entity(invite_link)
        print(f'\n✅ Канал найден!')
        print(f'   Название: {entity.title}')
        print(f'   ID: {entity.id}')
        print(f'   Username: @{entity.username}' if entity.username else '   Username: отсутствует')
        print(f'   Участников: {getattr(entity, "participants_count", "неизвестно")}')
        
        # Пробуем получить сообщения
        print(f'\n📥 Пробуем получить последние сообщения...')
        messages = await client.get_messages(entity, limit=5)
        if messages:
            print(f'   ✅ Получено {len(messages)} сообщений')
            for i, msg in enumerate(messages, 1):
                text_preview = msg.text[:150] if msg.text else '[нет текста]'
                print(f'   {i}. [{msg.date.strftime("%Y-%m-%d %H:%M")}] {text_preview}...')
            print(f'\n✅ Доступ есть — канал можно парсить!')
        else:
            print(f'   ⚠️ Сообщений нет (возможно, пустой канал)')
            
    except InviteHashExpiredError:
        print(f'❌ Ссылка истекла (InviteHashExpiredError)')
    except InviteHashInvalidError:
        print(f'❌ Ссылка недействительна (InviteHashInvalidError)')
    except Exception as e:
        print(f'❌ Ошибка: {type(e).__name__}: {e}')

    await client.disconnect()

asyncio.run(main())
