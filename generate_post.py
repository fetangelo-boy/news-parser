#!/usr/bin/env python3
"""
Генератор постов для Telegram-канала трейдеров.
После генерации текст проходит через редактора (второй запрос к DeepSeek)
для устранения AI-стиля, длинных тире, клише и воды.
Дополнительно отправляет отдельные сообщения с контекстом новостей
и описанием сюжета для иллюстрации.
"""

import os
import sys
import json
import argparse
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# ---------- Конфигурация ----------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Папки с планами и скиллами
BASE_DIR = Path(__file__).parent
POST_TYPES = ["psychology", "theory", "motivation", "indices"]

# ---------- Вспомогательные функции ----------
def read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    """Универсальный вызов DeepSeek API."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 3000
    }
    response = requests.post(DEEPSEEK_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

def edit_post(raw_text: str) -> str:
    """
    Редактирует сгенерированный текст, чтобы убрать AI-стиль,
    длинные тире, клише, воду и сделать текст естественным.
    """
    system_edit = (
        "Ты — профессиональный литературный редактор. Твоя задача — переписать предоставленный текст "
        "так, чтобы он звучал максимально естественно, как если бы его написал человек-эксперт, "
        "а не нейросеть. Строго соблюдай следующие правила:\n\n"
        "1. Пиши короткими простыми предложениями. Разбивай длинные конструкции.\n"
        "2. Убирай все клише, маркетинговые штампы и шаблонные фразы (например, 'Давайте посмотрим', "
        "'в этой статье мы разберём', 'как мы видим', 'следует отметить').\n"
        "3. Убирай все риторические вопросы. Переформулируй их как утверждения.\n"
        "4. Убирай фразы для вовлечения ('вы наверняка замечали', 'знакомо?', 'согласитесь').\n"
        "5. Убирай лишние слова, воду, повторы. Оставляй только суть.\n"
        "6. Используй разговорную грамматику, но без сленга. Пиши как в обычной человеческой речи.\n"
        "7. Без пафоса и лишних обещаний. Главное — ясность и смысл.\n"
        "8. Запрещено использовать длинное тире '—'. Заменяй на обычный дефис '-' или точку. Это критическое требование.\n"
        "9. Запрещено использовать двоеточие, кроме случаев, когда оно уже было в исходном тексте "
        "(например, в заголовках или перечислениях). Не добавляй новые двоеточия.\n"
        "10. Не используй шаблонные связки ('во-первых', 'во-вторых') и не перегружай текст перечислениями.\n"
        "11. Сохрани все факты, цифры, практические инструменты и структуру (если она была).\n"
        "12. Итоговый текст должен быть примерно той же длины (1500-2000 знаков), но более плотным по смыслу.\n\n"
        "Верни только исправленный текст, без пояснений и без обрамления."
    )
    user_edit = f"Отредактируй следующий текст:\n\n{raw_text}"
    edited = call_deepseek(system_edit, user_edit)
    
    # ---- ЖЁСТКАЯ ПОСТОБРАБОТКА ----
    # 1. Заменяем все длинные тире на дефисы
    edited = edited.replace("—", "-")
    # 2. Убираем двойные дефисы (если случайно появились)
    edited = edited.replace("--", "-")
    # 3. Убираем множественные пробелы
    edited = re.sub(r'\s+', ' ', edited)
    # 4. Убираем пробелы перед знаками препинания (.,!?:)
    edited = re.sub(r'\s+([.,!?:])', r'\1', edited)
    # 5. Приводим кавычки к единообразию (опционально, можно отключить)
    # edited = edited.replace("«", '"').replace("»", '"')
    
    return edited

def send_to_telegram(text: str) -> None:
    """Отправляет сообщение в технический Telegram-канал."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()

def send_news_context(news_text: str) -> None:
    """Отправляет отдельное сообщение с новостным контекстом."""
    if not news_text:
        message = "⚠️ Новостей для контекста не было (файл news_for_article.txt пуст или отсутствовал)."
    else:
        # Обрезаем, если слишком длинное
        if len(news_text) > 3000:
            news_text = news_text[:3000] + "...\n(обрезано)"
        message = f"📰 **Новости, использованные для генерации поста:**\n\n{news_text}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload).raise_for_status()

def generate_illustration_prompt(post_text: str) -> str:
    """Генерирует описание сюжета для иллюстрации на основе поста."""
    system_prompt = (
        "Ты — художник-иллюстратор. Твоя задача — по тексту поста для трейдеров придумать "
        "конкретный, яркий и визуальный сюжет для иллюстрации. "
        "Опиши сцену, персонажей, детали, цвета, атмосферу. "
        "Сделай это в виде короткого промпта (2-3 предложения), который можно отправить в нейросеть. "
        "Избегай абстракций, дай чёткие образы."
    )
    user_prompt = f"Пост:\n{post_text[:2000]}\n\nПридумай описание иллюстрации."
    return call_deepseek(system_prompt, user_prompt)

def send_illustration_prompt(prompt: str) -> None:
    """Отправляет описание иллюстрации отдельным сообщением."""
    message = f"🎨 **Сюжет для иллюстрации к посту:**\n\n{prompt}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload).raise_for_status()

def generate_post(post_type: str) -> str:
    """
    Генерирует пост через DeepSeek на основе плана и скилла.
    Возвращает сырой текст.
    """
    if post_type not in POST_TYPES:
        raise ValueError(f"Неизвестный тип: {post_type}. Доступны: {POST_TYPES}")

    type_dir = BASE_DIR / post_type
    plan_path = type_dir / "plan.md"
    skill_path = type_dir / "skill.md"
    current_path = type_dir / "current.txt"

    # Читаем текущий номер поста
    if current_path.exists():
        current_num = int(read_file(current_path))
    else:
        current_num = 1

    # Читаем план и находим нужную тему
    plan_text = read_file(plan_path)
    lines = plan_text.splitlines()
    topic = None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{current_num}.") or line.strip().startswith(f"{current_num})"):
            topic = line.strip()
            description = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(tuple(f"{n}." for n in range(1, 10))):
                description.append(lines[j].strip())
                j += 1
            topic += " " + " ".join(description)
            break
    if not topic:
        topic = f"Пост №{current_num} из плана"

    # Читаем скилл
    skill_text = read_file(skill_path)

    # Загружаем новости (из news_for_article.txt, если есть)
    news_path = BASE_DIR / "news_for_article.txt"
    news_text = ""
    if news_path.exists():
        news_text = read_file(news_path)

    # Системный промпт
    system_prompt = (
        "Ты — автор постов для Telegram-канала трейдеров. "
        "Твоя задача — написать пост на заданную тему, строго следуя правилам стиля и используя свежие новости, "
        "если они релевантны. \n\n"
        "Правила стиля:\n" + skill_text + "\n\n"
        "Структура поста: хук (не риторический вопрос!), вступление, 3-5 пунктов, практический инструмент, "
        "честный подвох, призыв к действию (без фразы 'Сохраните этот пост')."
    )

    user_prompt = (
        f"Тема поста: {topic}\n"
        f"Новости для контекста (используй только если они подходят):\n{news_text}\n\n"
        "Напиши пост."
    )

    raw_post = call_deepseek(system_prompt, user_prompt)

    # Инкремент current.txt (для автоматического режима)
    current_num += 1
    with open(current_path, "w", encoding="utf-8") as f:
        f.write(str(current_num))

    return raw_post

def main():
    parser = argparse.ArgumentParser(description="Генератор постов для Telegram-канала трейдеров")
    parser.add_argument("--type", required=True, choices=POST_TYPES,
                        help="Тип поста: psychology, theory, motivation, indices")
    args = parser.parse_args()
    post_type = args.type

    try:
        print(f"Генерация поста типа '{post_type}'...")
        raw = generate_post(post_type)

        print("Редактирование текста (убираем AI-стиль)...")
        edited = edit_post(raw)

        # ---- НОВЫЕ ШАГИ ----
        # 1. Отправляем контекст новостей (читаем файл заново, чтобы показать, что использовалось)
        news_path = BASE_DIR / "news_for_article.txt"
        news_text = ""
        if news_path.exists():
            news_text = read_file(news_path)
        send_news_context(news_text)

        # 2. Отправляем основной пост
        print("Отправка поста в Telegram...")
        send_to_telegram(edited)

        # 3. Генерируем и отправляем описание иллюстрации
        print("Генерация описания иллюстрации...")
        illustration_prompt = generate_illustration_prompt(edited)
        send_illustration_prompt(illustration_prompt)

        print("✅ Пост сгенерирован, отредактирован и отправлен.")
        print("✅ Контекст новостей и описание иллюстрации также отправлены.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
