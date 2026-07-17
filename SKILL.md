# Навык: Парсер новостей из Telegram

## Описание
Собирает новости из Telegram-каналов (включая приватные по invite-ссылке), сохраняет в SQLite-базу и публикует свежий дайджест за 5 дней в файл `news_for_article.txt` прямо в репозиторий. Запускается по расписанию через GitHub Actions.

## Источники

### Публичные каналы
- `Trader3P`
- `stocksi`
- `@moex_official`
- `@rbc_news`
- `@tass_agency`
- `@markettwits`

### Приватные каналы (доступ по invite-ссылке)
- `Full-Time Trading`

Список расширяется в переменной `CHANNELS` в `parser.py`. Приватные каналы задаются как `{'name': 'Название', 'invite_hash': 'xxx'}`.

## Структура проекта
- `parser.py` — основной скрипт парсинга (Telethon). Поддерживает публичные и приватные каналы.
- `export_last_news.py` — экспортирует последние 100 новостей за 5 дней в `news_for_article.txt` (600 символов на пост, с фильтрацией рекламы и подписок).
- `.github/workflows/parser.yml` — GitHub Actions workflow (авто-коммит дайджеста в репозиторий).
- `news.db` — SQLite-база накопленных новостей (кэшируется между запусками).
- `parser_session.session` — сессия Telethon (аутентификация).

## Фильтрация текста
При экспорте из текста удаляются:
- Строки с ключевыми словами: «подписаться», «реклама», «партнёрский», «промокод», «t.me/+» и др.
- Markdown-ссылки `[текст](url)` — остаётся только текст ссылки.
- Голые URL-ссылки на Telegram.

## Результат
После каждого запуска файл `news_for_article.txt` автоматически коммитится в репозиторий. Доступен на главной странице: https://github.com/fetangelo-boy/news-parser

## Запуск
1. Перейти на https://github.com/fetangelo-boy/news-parser
2. **Actions** → **Daily News Parser** → **Run workflow**
3. Через ~3 мин обновится файл `news_for_article.txt` в корне репозитория

## Требуемые секреты GitHub
- `API_ID` — Telegram API ID
- `API_HASH` — Telegram API Hash
- `SESSION_BASE64` — base64 сессии Telethon

### Как получить SESSION_BASE64
```bash
python -c "import base64; open('session_base64.txt','w').write(base64.b64encode(open('parser_session.session','rb').read()).decode())"
```
Скопировать содержимое `session_base64.txt` в секрет `SESSION_BASE64` на GitHub.

## Расписание
4 раза в день по Москве: 00:00, 06:00, 12:00, 18:00.
