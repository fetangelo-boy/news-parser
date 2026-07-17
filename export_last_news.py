import sqlite3
import datetime
import re

DB_FILE = 'news.db'
OUTPUT_FILE = 'news_for_article.txt'
DAYS_BACK = 5
LIMIT = 100            # уменьшил со 150 до 100
MAX_TEXT_LENGTH = 600   # уменьшил с 1000 до 600 символов на пост

# Слова-маркеры рекламы/подписок — строки с ними удаляются из текста
FILTER_KEYWORDS = [
    'подписаться', 'подпишись', 'подписка', 'оформить подписку',
    'реклама', '#реклама', 'партнёрский', 'партнерский',
    'рекламный', 'промокод', 'спонсор',
    'нажми сюда', 'переходи по ссылке', 'переходите по ссылке',
    'успей купить', 'скидка', 'акция',
    't.me/+',     # invite-ссылки
    'tg link',
]


def clean_text(text: str) -> str:
    """Очищает текст от рекламных строк и лишних ссылок."""
    if not text:
        return ''

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        lower = line.lower().strip()

        # Пропускаем пустые строки
        if not lower:
            continue

        # Пропускаем строки с ключевыми словами
        skip = False
        for kw in FILTER_KEYWORDS:
            if kw in lower:
                skip = True
                break
        if skip:
            continue

        # Убираем markdown-ссылки вида [текст](url) — оставляем только текст
        line = re.sub(r'\[([^\]]*)\]\(https?://[^\)]+\)', r'\1', line)

        # Убираем голые URL-ссылки, оставляя текст после них (если есть)
        # Ссылки вида https://... — удаляем, оставляем пусто
        line = re.sub(r'https?://t\.me/\+[^\s]+', '', line)

        # Сворачиваем множественные пробелы
        line = re.sub(r' {2,}', ' ', line).strip()

        if line:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def export_recent_news():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    cutoff = (datetime.datetime.now() - datetime.timedelta(days=DAYS_BACK)).isoformat()

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

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        f.write(f'Дайджест новостей за {DAYS_BACK} дней ({now_str})\n')
        f.write(f'Всего записей: {len(rows)}\n')
        f.write('=' * 50 + '\n\n')

        for i, (source, date, text) in enumerate(rows, 1):
            # Очищаем текст от рекламы и подписок
            clean = clean_text(text)
            if not clean:
                continue  # если текст целиком состоял из рекламы — пропускаем пост

            f.write(f'{i}. [{source}] {date[:16]}\n')
            f.write(f'{clean[:MAX_TEXT_LENGTH]}\n')
            if len(clean) > MAX_TEXT_LENGTH:
                f.write('   ...\n')
            f.write('\n')

    print(f'✅ Готово. Файл {OUTPUT_FILE} сохранён, {len(rows)} новостей за {DAYS_BACK} дней.')


if __name__ == '__main__':
    export_recent_news()