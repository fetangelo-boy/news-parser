# Навык: Парсер новостей из Telegram

## Описание
Собирает новости из заданных Telegram-каналов (включая приватные по invite-ссылке), сохраняет их в SQLite-базу и экспортирует свежие новости за 5 дней в TXT-файл. Запускается по расписанию через GitHub Actions.

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
- `parser.py` — основной скрипт парсинга (Telethon). Поддерживает публичные каналы по username и приватные по invite-хэшу.
- `export_last_news.py` — экспортирует новости за последние 5 дней из `news.db` в `news_for_article.txt`.
- `.githubworkflows/parser.yml` — GitHub Actions workflow (TXT-артефакт: `свежие-новости`).
- `news.db` — SQLite-база накопленных новостей.
- `parser_session.session` — сессия Telethon (аутентификация).

## Как работает накопление
- База данных `news.db` кэшируется между запусками (благодаря `actions/cache`).
- Поле `raw_message_id` имеет ограничение `UNIQUE` — дублирующиеся сообщения игнорируются.
- После каждого запуска создаётся артефакт `свежие-новости` с TXT-файлом последних новостей за 5 дней.

## Запуск
1. Перейти в раздел **Actions** репозитория.
2. Выбрать workflow **"Daily News Parser"**.
3. Нажать **"Run workflow"**.
4. Скачать артефакт `свежие-новости` после завершения — внутри `news_for_article.txt`.

## Требуемые секреты GitHub
- `API_ID` — ваш Telegram API ID
- `API_HASH` — ваш Telegram API Hash
- `SESSION_BASE64` — base64-кодированная сессия Telethon (`parser_session.session`)

### Как получить SESSION_BASE64
1. Убедитесь, что локально есть рабочий `parser_session.session`.
2. Выполните в терминале:
   ```
   base64 parser_session.session > session_base64.txt
   ```
   (на Windows — используйте Git Bash или онлайн-конвертер)
3. Скопируйте содержимое в секрет `SESSION_BASE64` на GitHub.

## Расписание
4 раза в день по Москве: 00:00, 06:00, 12:00, 18:00.