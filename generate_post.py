#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import datetime
import requests
import time
from pathlib import Path

# ===== НАСТРОЙКИ =====
PLAN_FILE = 'deepseek_plan_statei.md'
SKILL_FILE = 'SKILL.md'
NEWS_EXPORT_SCRIPT = 'export_last_news.py'
OUTPUT_DIR = 'generated_posts'

# Telegram
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')  # ваш личный ID для уведомлений

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

# ===== ОПРЕДЕЛЕНИЕ ПОСТА ПО ДНЮ НЕДЕЛИ =====
def get_post_info():
    today = datetime.datetime.now()
    weekday = today.weekday()
    if weekday == 2:  # среда
        return {
            'day': 'среда',
            'cycle': 'Цикл 2. Биохимия депозита',
            'post_number': 2,
            'title': 'Тестостероновый драйв: когда уверенность становится убийцей',
            'theme': 'психология'
        }
    elif weekday == 5:  # суббота
        return {
            'day': 'суббота',
            'cycle': 'Цикл 1. Технический анализ',
            'post_number': 1,
            'title': 'Заглушка для теории',
            'theme': 'теория'
        }
    else:
        return {
            'day': 'тест',
            'cycle': 'Тестовый цикл',
            'post_number': 0,
            'title': 'Тестовый пост',
            'theme': 'тест'
        }

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

def read_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️ Файл {filename} не найден.")
        return ""

# ===== ФОРМИРОВАНИЕ ПРОМПТА =====
def build_prompt(post_info, news_text, skill_text, plan_text):
    prompt = f"""Ты — копирайтер для Telegram-канала трейдеров. Твоя задача — написать пост на тему "{post_info['title']}" (цикл: {post_info['cycle']}).

Новости должны использоваться только как живые примеры для иллюстрации психологических/теоретических тезисов поста. Не подгоняй содержание поста под новости. Пост должен соответствовать теме из плана, а новости — лишь подсвечивать её.

**Свежие новости (за последние 5 дней):**
{news_text}

**Правила стиля (из SKILL.md):**
{skill_text}

**План статей (для контекста):**
{plan_text}

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
    print("🚀 Генерация поста...")
    post_info = get_post_info()
    print(f"📝 Тема: {post_info['title']}")
    print(f"📅 День: {post_info['day']}")

    # 1. Сбор новостей
    run_news_export()
    news_text = read_news()
    has_news = "Нет свежих новостей" not in news_text

    # 2. Чтение SKILL и плана
    skill_text = read_file(SKILL_FILE)
    plan_text = read_file(PLAN_FILE)

    # 3. Формирование промпта и вызов DeepSeek
    prompt = build_prompt(post_info, news_text, skill_text, plan_text)
    print("⏳ Ожидание ответа от DeepSeek...")
    result = call_deepseek(prompt)

    # 4. Сохраняем пост в файл (для истории)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = f"{OUTPUT_DIR}/post_{post_info['theme']}_{date_str}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"✅ Пост сохранён в {filename}")

    # 5. Подготовка доклада
    report = f"""📋 **Доклад по генерации поста**
- План: {post_info['cycle']}
- Пост №{post_info['post_number']}: **{post_info['title']}**
- День публикации: {post_info['day']}
- Новости использованы: {"✅ да" if has_news else "❌ нет"}
- Дата генерации: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    # 6. Отправка доклада в канал
    if BOT_TOKEN and CHAT_ID:
        send_telegram_with_retry(report, parse_mode='Markdown')
        # Отправка самого поста
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
