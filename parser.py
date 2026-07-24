#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import sqlite3
import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError

# ===== ЧТЕНИЕ КЛЮЧЕЙ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
if not API_ID or not API_HASH:
    raise ValueError("API_ID и API_HASH должны быть заданы в переменных окружения")

# Список каналов
#   строка — публичный канал (username или @username)
#   dict — приватный канал: {'name': 'Название', 'invite_hash': 'xxx'}
CHANNELS = [
    'Trader3P',
    'stocksi',
    '@moex_official',
    '@rbc_news',
    '@tass_agency',
    'https://t.me/cbrstocks',
    'https://t.me/cbrstocks/61357',
    '@markettwits',
    {'name': 'Full-Time Trading', 'invite_hash': '-_V19XANAdFkOWFi'},
]

LIMIT_PER_CHANNEL = 150
MAX_TEXT_LENGTH = 5000
DB_FILE = 'news.db'
SESSION_NAME = 'parser_session'

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            published_at DATETIME NOT NULL,
            text TEXT,
            raw_message_id TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_published ON news(published_at)')
    conn.commit()
    conn.close()


def save_message(source, date, text, msg_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO news (source, published_at, text, raw_message_id)
            VALUES (?, ?, ?, ?)
        ''', (source, date.isoformat(), text[:MAX_TEXT_LENGTH], str(msg_id)))
        conn.commit()
        print(f'  [+] Сохранено: {source} | {date.strftime("%Y-%m-%d %H:%M")}')
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


# ===== РАЗРЕШЕНИЕ КАНАЛА (публичный / приватный) =====
async def resolve_channel(client, channel_def):
    """Принимает строку (username) или dict с invite_hash. Возвращает (entity, display_name)."""
    if isinstance(channel_def, dict):
        name = channel_def.get('name', 'Неизвестный канал')
        invite_hash = channel_def.get('invite_hash', '')
        if invite_hash:
            invite_link = f'https://t.me/+{invite_hash}'
            try:
                entity = await client.get_entity(invite_link)
                print(f'  → Канал найден по invite-ссылке: {entity.title}')
                return entity, entity.title or name
            except Exception as e:
                print(f'  ⚠ Не удалось получить канал по invite: {e}')
        # Fallback: поиск по названию среди подписок
        print(f'  🔍 Поиск канала "{name}" среди подписок...')
        async for dialog in client.iter_dialogs():
            if dialog.is_channel and (dialog.name == name or name in dialog.name):
                print(f'  → Найден в подписках: {dialog.name}')
                return dialog.entity, dialog.name
        raise ValueError(f'Канал "{name}" не найден ни по invite, ни в подписках')

    # Публичный канал — строка
    username = channel_def
    display_name = username.lstrip('@')
    entity = await client.get_entity(username)
    return entity, display_name


# ===== ПАРСИНГ =====
async def parse_channels():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.start()
        print('✓ Подключено к Telegram API')
        print(f'📡 Будет просканировано каналов: {len(CHANNELS)}')
        print('-' * 50)

        total_saved = 0
        for channel_def in CHANNELS:
            # Отображаем имя канала
            if isinstance(channel_def, dict):
                display_name = channel_def.get('name', 'Приватный канал')
            else:
                display_name = channel_def.lstrip('@')
            print(f'→ Обработка канала: {display_name}')

            try:
                entity, source_name = await resolve_channel(client, channel_def)
            except UsernameNotOccupiedError:
                print(f'  ✗ Канал {display_name} не найден')
                continue
            except ChannelPrivateError:
                print(f'  ✗ Канал {display_name} приватный (нет доступа)')
                continue
            except ValueError as e:
                print(f'  ✗ {e}')
                continue
            except Exception as e:
                print(f'  ✗ Ошибка: {e}')
                continue

            try:
                messages = await client.get_messages(entity, limit=LIMIT_PER_CHANNEL)
                print(f'  Получено {len(messages)} сообщений')
                saved_count = 0
                for msg in messages:
                    if not msg.text or len(msg.text.strip()) < 10:
                        continue
                    # Фильтр рекламы
                    text_lower = msg.text.lower()
                    if 'реклама' in text_lower or 'партнёрский' in text_lower or '#реклама' in text_lower:
                        continue
                    save_message(source_name, msg.date, msg.text, msg.id)
                    saved_count += 1
                print(f'  ✓ Сохранено новых: {saved_count}')
                total_saved += saved_count
            except FloodWaitError as e:
                print(f'  ⚠ Пауза {e.seconds} секунд')
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f'  ✗ Ошибка при получении сообщений: {e}')

        print('-' * 50)
        print(f'✅ Готово. Всего сохранено: {total_saved}')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    finally:
        await client.disconnect()
        print('🔌 Соединение закрыто')


if __name__ == '__main__':
    print('📰 Парсер новостей Telegram')
    print('=' * 50)
    init_db()
    asyncio.run(parse_channels())
