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
CHANNELS = [
    'Trader3P',
    'stocksi',
    '+-_V19XANAdFkOWFi',
    '@moex_official',
    '@rbc_news',
    '@tass_agency'
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

# ===== ПАРСИНГ =====
async def parse_channels():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.start()
        print('✓ Подключено к Telegram API')
        print(f'📡 Будет просканировано каналов: {len(CHANNELS)}')
        print('-' * 50)
        
        total_saved = 0
        for username in CHANNELS:
            print(f'→ Обработка канала: {username}')
            try:
                entity = await client.get_entity(username)
            except UsernameNotOccupiedError:
                print(f'  ✗ Канал {username} не найден')
                continue
            except ChannelPrivateError:
                print(f'  ✗ Канал {username} приватный')
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
                    save_message(username, msg.date, msg.text, msg.id)
                    saved_count += 1
                print(f'  ✓ Сохранено новых: {saved_count}')
                total_saved += saved_count
            except FloodWaitError as e:
                print(f'  ⚠ Пауза {e.seconds} секунд')
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f'  ✗ Ошибка: {e}')
        
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
