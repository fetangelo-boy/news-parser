import sqlite3
import datetime

DB_FILE = 'news.db'
OUTPUT_FILE = 'news_for_article.txt'
DAYS_BACK = 5           # период в днях
LIMIT = 150             # максимум записей

def export_recent_news():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Вычисляем дату 5 дней назад от текущего момента
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=DAYS_BACK)).isoformat()

    # Запрос: новости за последние 5 дней, сортировка по дате (свежие сверху), ограничение 150
    c.execute('''
        SELECT source, published_at, text
        FROM news
        WHERE published_at >= ?
        ORDER BY published_at DESC
        LIMIT ?
    ''', (cutoff, LIMIT))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f'Нет новостей за последние {DAYS_BACK} дней.')
        return

    # Запись в текстовый файл
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f'Новости за последние {DAYS_BACK} дней (выгружено {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})\n')
        f.write(f'Всего записей: {len(rows)}\n')
        f.write('=' * 60 + '\n\n')

        for i, (source, date, text) in enumerate(rows, 1):
            f.write(f'{i}. Источник: {source}\n')
            f.write(f'   Дата: {date[:16]}\n')
            f.write(f'   Текст: {text[:1000]}\n')
            if len(text) > 1000:
                f.write('   ... (продолжение в базе)\n')
            f.write('\n' + '-' * 40 + '\n\n')

    print(f'✅ Готово. Файл {OUTPUT_FILE} создан, содержит {len(rows)} новостей за последние {DAYS_BACK} дней.')

if __name__ == '__main__':
    export_recent_news()