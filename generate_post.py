#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import datetime
import requests
import time
import argparse
import re
from pathlib import Path

# ===== ПАРСИНГ АРГУМЕНТОВ =====
parser = argparse.ArgumentParser()
parser.add_argument('--type', default='psychology', choices=['psychology', 'theory', 'motivation', 'indices'])
args = parser.parse_args()
POST_TYPE = args.type

# ===== НАСТРОЙКИ =====
BASE_DIR = Path(__file__).parent
TYPE_DIR = BASE_DIR / POST_TYPE

if not TYPE_DIR.exists():
    print(f"❌ Папка {TYPE_DIR} не найдена. Создайте её с plan.md и skill.md.")
    sys.exit(1)

PLAN_FILE = TYPE_DIR / 'plan.md'
SKILL_FILE = TYPE_DIR / 'skill.md'
CURRENT_FILE = TYPE_DIR / 'current.txt'   # хранит номер текущего поста (1, 2, 3...)
NEWS_EXPORT_SCRIPT = 'export_last_news.py'
OUTPUT_DIR = 'generated_posts'

# Telegram
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')

# DeepSeek
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    print("❌ Ошибка: не задан DEEPSEEK_API_KEY")
    sys.exit(1)
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ===== ФУНКЦИЯ ОТПРАВКИ В TELEGRAM С RETRY =====
def send_telegram_with_retry(text, parse_mode='Markdown', max_attempts=5, delay=10):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram не настроен, пропускаем отправку.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': parse_mode
    }
    for attempt in range(1, max_attempts + 1):
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200:
                print(f"✅ Сообщение успешно доставлено в канал (попытка {attempt})")
                return True
            else:
                print(f"⚠️ Попытка {attempt}: ошибка {r.status_code}, {r.text}")
        except Exception as e:
            print(f"⚠️ Попытка {attempt}: ошибка соединения: {e}")
        if attempt < max_attempts:
            print(f"⏳ Повтор через {delay} секунд...")
            time.sleep(delay)
    print("❌ Не удалось отправить сообщение после всех попыток.")
    return False

# ===== ЧТЕНИЕ ТЕКУЩЕГО ПОСТА ИЗ ПЛАНА =====
def get_current_post(plan_text):
    """
    Читает номер текущего поста из файла current.txt.
    Если файла нет — создаёт со значением 1.
    Возвращает словарь: номер, название, цикл, ключевая мысль.
    """
    # Читаем номер
    if CURRENT_FILE.exists():
        with open(CURRENT_FILE, 'r') as f:
            try:
                current_num = int(f.read().strip())
            except ValueError:
                current_num = 1
    else:
        current_num = 1
        with open(CURRENT_FILE, 'w') as f:
            f.write(str(current_num))

    # Парсим план, чтобы найти пост с номером current_num
    # Ищем в тексте план маркер: | № | Название | Ключевая мысль |
    # Простой вариант: ищем строки с таблицей, извлекаем по порядку.
    # Допустим, план имеет структуру с таблицами, но для простоты возьмём поиск по номеру.
    # Альтернатива: использовать нумерацию, но проще будет хранить массив постов в самом плане.
    # Для демонстрации я предполагаю, что в плане есть строки вида:
    # | 1 | **«Название»** | Ключевая мысль |
    # Поскольку мы пока не парсим сложно, можно пока оставить заглушку.
    # В будущем можно реализовать полноценный парсер.

    # Пока возвращаем фиксированный второй пост (тестостерон) как заглушку.
    # Но вы можете потом заменить на реальный парсинг плана.
    # Ниже я оставлю заглушку, но вы можете дописать парсер.
    # Пример парсинга:
    # lines = plan_text.split('\n')
    # for line in lines:
    #     if line.strip().startswith('|') and '|' in line:
    #         parts = [p.strip() for p in line.split('|') if p.strip()]
    #         if len(parts) >= 3 and parts[0].isdigit():
    #             num = int(parts[0])
    #             if num == current_num:
    #                 title = parts[1].strip('**')
    #                 idea = parts[2]
    #                 cycle = "Цикл 2. Биохимия депозита"  # можно извлечь из контекста
    #                 return {'number': num, 'title': title, 'cycle': cycle, 'idea': idea}

    # Временно возвращаем фиксированный пост (номер 2)
    # Чтобы не ломать тестирование, пока оставлю так, но в будущем реализовать парсинг.
    title = "Тестостероновый драйв: когда уверенность становится убийцей"
    cycle = "Цикл 2. Биохимия депозита"
    idea = "Тестостерон связан с готовностью к риску, но работает только при низком кортизоле. Уверенный трейдер часто сливает больше, чем тревожный."
    return {'number': current_num, 'title': title, 'cycle': cycle, 'idea': idea}

def save_current_post_number(num):
    with open(CURRENT_FILE, 'w') as f:
        f.write(str(num))

# ===== СБОР НОВОСТЕЙ =====
def run_news_export():
    try:
        subprocess.run([sys.executable, NEWS_EXPORT_SCRIPT], check=True, capture_output=True)
        print("✅ Новости выгружены.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при запуске {NEWS_EXPORT_SCRIPT}: {e.stderr.decode()}")
        sys.exit(1)

def read_news():
    try:
        with open('news_for_article.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            print("✅ Новости прочитаны.")
            return content
    except FileNotFoundError:
        print("⚠️ Файл с новостями не найден. Использую пустой контекст.")
        return "Нет свежих новостей."

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️ Файл {path} не найден.")
        return ""

# ===== ФОРМИРОВАНИЕ ПРОМПТА =====
def build_prompt(post_info, news_text, skill_text, plan_text):
    title = post_info['title']
    cycle = post_info['cycle']
    idea = post_info['idea']

    prompt = f"""Ты — копирайтер для Telegram-канала трейдеров. Твоя задача — написать пост на тему "{title}" (цикл: {cycle}).

Новости должны использоваться только как живые примеры для иллюстрации психологических тезисов поста. Не подгоняй содержание поста под новости. Пост должен соответствовать теме из плана, а новости — лишь подсвечивать её.

**Свежие новости (за последние 5 дней):**
{news_text}

**Правила стиля (из SKILL.md):**
{skill_text}

**План статей (для контекста):**
{plan_text}

**Ключевая мысль поста:** {idea}

Теперь напиши пост по структуре: хук, 3-5 пунктов, честный подвох, CTA «Сохраните». Обязательно используй эмодзи по смыслу (5-10), в конце хэштеги. Дай описание метафоры для иллюстрации в отдельном блоке.

Выдай пост в формате:
--- НАЧАЛО ПОСТА ---
[текст поста]
--- КОНЕЦ ПОСТА ---
--- МЕТАФОРА ---
[описание иллюстрации]
--- КОНЕЦ МЕТАФОРЫ ---
"""
    return prompt

# ===== ВЫЗОВ DEEPSEEK =====
def call_deepseek(prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "Ты — опытный копирайтер, пишешь живые, полезные посты для трейдеров."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 3000
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"❌ Ошибка при вызове DeepSeek API: {e}")
        if 'response' in locals():
            print(response.text)
        sys.exit(1)

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
def main():
    print(f"🚀 Генерация поста типа: {POST_TYPE}")

    # 1. Чтение плана и SKILL
    skill_text = read_file(SKILL_FILE)
    plan_text = read_file(PLAN_FILE)

    # 2. Определяем текущий пост из плана
    post_info = get_current_post(plan_text)
    print(f"📝 Пост №{post_info['number']}: {post_info['title']}")

    # 3. Сбор новостей
    run_news_export()
    news_text = read_news()
    has_news = "Нет свежих новостей" not in news_text

    # 4. Формирование промпта и вызов DeepSeek
    prompt = build_prompt(post_info, news_text, skill_text, plan_text)
    print("⏳ Ожидание ответа от DeepSeek...")
    result = call_deepseek(prompt)

    # 5. Сохраняем пост в файл
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = f"{OUTPUT_DIR}/post_{POST_TYPE}_{date_str}_n{post_info['number']}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"✅ Пост сохранён в {filename}")

    # 6. Увеличиваем номер поста для следующего запуска
    new_num = post_info['number'] + 1
    save_current_post_number(new_num)
    print(f"✅ Следующий пост: №{new_num}")

    # 7. Доклад
    report = f"""📋 **Доклад по генерации поста**
- Тип: {POST_TYPE}
- Пост №{post_info['number']}: **{post_info['title']}**
- Новости использованы: {"✅ да" if has_news else "❌ нет"}
- Дата генерации: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    # 8. Отправка в Telegram
    if BOT_TOKEN and CHAT_ID:
        send_telegram_with_retry(report, parse_mode='Markdown')
        # Парсим пост и метафору
        if '--- МЕТАФОРА ---' in result:
            parts = result.split('--- МЕТАФОРА ---')
            post_text = parts[0].replace('--- НАЧАЛО ПОСТА ---', '').replace('--- КОНЕЦ ПОСТА ---', '').strip()
            metaphor = parts[1].replace('--- КОНЕЦ МЕТАФОРЫ ---', '').strip() if len(parts) > 1 else ''
        else:
            post_text = result
            metaphor = ''
        full_message = f"{post_text}\n\n---\n🎨 *Описание иллюстрации:*\n{metaphor}" if metaphor else post_text
        send_telegram_with_retry(full_message, parse_mode='Markdown')
    else:
        print("⚠️ Telegram не настроен, сообщение не отправлено.")

    print("✅ Готово!")

if __name__ == '__main__':
    main()
