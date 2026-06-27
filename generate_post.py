#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_post.py — автоматическая генерация поста для Telegram-канала
по плану статей с использованием свежих новостей и правил стиля (SKILL.md).
Поддерживает два режима: психология (среда) и теория (суббота).
"""

import os
import sys
import subprocess
import json
import datetime
import re
import requests
from pathlib import Path

# ===== НАСТРОЙКИ =====
PLAN_FILE = 'deepseek_plan_statei.md'   # план статей
SKILL_FILE = 'SKILL.md'                  # правила стиля
NEWS_EXPORT_SCRIPT = 'export_last_news.py'
NEWS_FILE = 'news_for_article.txt'
OUTPUT_DIR = 'generated_posts'           # папка для готовых черновиков

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    # если ключ не задан в окружении, попробуем прочитать из локального файла (не рекомендуется)
    try:
        with open('deepseek_key.txt', 'r') as f:
            DEEPSEEK_API_KEY = f.read().strip()
    except FileNotFoundError:
        print("❌ Ошибка: не задан DEEPSEEK_API_KEY. Установите переменную окружения или создайте файл deepseek_key.txt.")
        sys.exit(1)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # или "deepseek-reasoner" для более глубокого анализа

# ===== ФУНКЦИИ =====

def get_current_post_info():
    """
    Определяет, какой пост нужно написать сегодня, основываясь на дне недели.
    Возвращает словарь с ключами: cycle, post_number, title, day.
    Сейчас мы пишем только средний пост (психология) и субботний (теория).
    Для простоты сначала реализуем только средний (психология).
    """
    today = datetime.datetime.now()
    weekday = today.weekday()  # 0=понедельник, 2=среда, 5=суббота

    # Сопоставление дня недели с постом
    # Пока что только среда = психология, суббота = теория (но теорию пока не реализуем)
    if weekday == 2:  # среда
        return {
            'day': 'среда',
            'cycle': 'Цикл 2. Биохимия депозита',
            'post_number': 2,  # второй пост цикла (тестостероновый драйв) — после кортизола
            'title': 'Тестостероновый драйв: когда уверенность становится убийцей',
            'theme': 'психология'
        }
    elif weekday == 5:  # суббота
        # Позже добавим логику для теории
        return {
            'day': 'суббота',
            'cycle': 'Цикл 1. Технический анализ',
            'post_number': 1,
            'title': 'Пока заглушка для теории',
            'theme': 'теория'
        }
    else:
        # Если сегодня не среда и не суббота, можно пропустить или сгенерировать дефолтный пост
        # Для теста можно вернуть среду
        print("Сегодня не среда и не суббота. Для теста генерируем средний пост.")
        return {
            'day': 'среда (тест)',
            'cycle': 'Цикл 2. Биохимия депозита',
            'post_number': 2,
            'title': 'Тестостероновый драйв: когда уверенность становится убийцей',
            'theme': 'психология'
        }


def run_news_export():
    """Запускает export_last_news.py, чтобы получить свежие новости."""
    try:
        subprocess.run([sys.executable, NEWS_EXPORT_SCRIPT], check=True)
        print("✅ Новости выгружены.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при запуске {NEWS_EXPORT_SCRIPT}: {e}")
        sys.exit(1)


def read_news():
    """Читает файл news_for_article.txt и возвращает текст новостей."""
    try:
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Файл {NEWS_FILE} не найден. Запустите export_last_news.py вручную.")
        sys.exit(1)


def read_skill():
    """Читает SKILL.md и возвращает его содержимое."""
    try:
        with open(SKILL_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Файл {SKILL_FILE} не найден.")
        sys.exit(1)


def read_plan():
    """Читает план статей (пока для справки, но можно не использовать, если мы жёстко задаём пост)."""
    try:
        with open(PLAN_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Файл {PLAN_FILE} не найден.")
        return ""


def build_prompt(post_info, news_text, skill_text):
    """
    Формирует промпт для DeepSeek на основе информации о посте, новостях и SKILL.
    """
    theme = post_info['theme']
    title = post_info['title']
    cycle = post_info['cycle']
    day = post_info['day']

    # Базовый промпт
    prompt = f"""Ты — копирайтер, который пишет посты для Telegram-канала для трейдеров. Твоя задача — написать пост по заданной теме, используя правила стиля из SKILL.md и свежие новости, если они релевантны.

# Правила стиля (из SKILL.md):
{skill_text}

# Тема поста:
{title}
Цикл: {cycle}
День публикации: {day}

# Свежие новости (за последние 5 дней):
{news_text}

# Задание:
Напиши пост на тему "{title}". Используй новости как живую иллюстрацию, если они связаны с темой (например, текущая ситуация на рынке, обвал, решения ЦБ и т.п.). Если новости не релевантны, просто напиши пост по теме без привязки к текущему фону.

Пост должен строго соответствовать структуре:
1. Заголовок-хук (интрига, не описание).
2. 3-5 пунктов с конкретикой и практическими выводами.
3. Честный подвох (ограничение метода).
4. CTA «Сохраните» (призыв сохранить или применить).

Требования к стилю: живой язык, короткие предложения, без шаблонов, без длинного тире, эмодзи по смыслу, в конце предложения с эмодзи точка не ставится. Умеренное количество эмодзи (5-10). В конце поста обязательно хэштеги: #трейдинг #психологияторговли #дисциплина #рискменеджмент #рефлексиитрейдера (или адаптируй под тему).

Длина поста — до 2000 знаков с пробелами.

Также дай краткое описание метафорической иллюстрации (для дизайнера) — 2-4 предложения, образ, связанный с основным посылом поста, без графиков и цифр.

Выдай пост в формате:
--- НАЧАЛО ПОСТА ---
[текст поста]
--- КОНЕЦ ПОСТА ---
--- МЕТАФОРА ---
[описание иллюстрации]
--- КОНЕЦ МЕТАФОРЫ ---
"""

    return prompt


def call_deepseek(prompt):
    """Отправляет запрос к DeepSeek API и возвращает ответ."""
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
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"❌ Ошибка при вызове DeepSeek API: {e}")
        if response:
            print(response.text)
        sys.exit(1)


def save_post(content, post_info):
    """Сохраняет готовый пост в файл."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = f"{OUTPUT_DIR}/post_{post_info['theme']}_{date_str}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Пост сохранён в {filename}")
    return filename


def main():
    print("🚀 Генерация поста...")
    
    # 1. Определяем, какой пост писать
    post_info = get_current_post_info()
    print(f"📝 Тема: {post_info['title']}")
    print(f"📅 День: {post_info['day']}")
    
    # 2. Запускаем сбор новостей
    run_news_export()
    
    # 3. Читаем новости и SKILL
    news_text = read_news()
    skill_text = read_skill()
    
    # 4. Формируем промпт
    prompt = build_prompt(post_info, news_text, skill_text)
    
    # 5. Отправляем в DeepSeek
    print("⏳ Ожидание ответа от DeepSeek...")
    result = call_deepseek(prompt)
    
    # 6. Сохраняем результат
    filename = save_post(result, post_info)
    
    print("✅ Готово!")
    print(f"📄 Файл: {filename}")
    print("\n--- Содержимое поста ---\n")
    print(result)
    print("\n--- Конец ---")


if __name__ == '__main__':
    main()