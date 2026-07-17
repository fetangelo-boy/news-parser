#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json

DB_FILE = 'news.db'
EXPORT_FILE = 'all_news.json'

def export_all():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT source, published_at, text, raw_message_id
        FROM news
        ORDER BY published_at DESC
    ''')
    rows = c.fetchall()
    data = []
    for row in rows:
        data.append({
            'source': row['source'],
            'published_at': row['published_at'],
            'text': row['text'],
            'message_id': row['raw_message_id']
        })
    conn.close()

    with open(EXPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'✅ Экспортировано {len(data)} записей в {EXPORT_FILE}')

if __name__ == '__main__':
    export_all()
