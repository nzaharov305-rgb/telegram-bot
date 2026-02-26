# Krisha Monitor SaaS Bot

Production-ready Telegram-бот для мониторинга объявлений Krisha.kz (Алматы).

## Стек

- Python 3.11
- aiogram 3.x
- asyncpg (PostgreSQL)
- aiohttp, BeautifulSoup4
- Railway-ready

## Тарифы

| Тариф | Цена | Интервал | Лимиты |
|-------|------|----------|--------|
| FREE | — | 10 мин | 1 район, 1 комната, 5 объявлений/день, trial 2ч |
| STANDARD | 4900 ₸ | 2 мин | Все районы, 1-3 комнаты |
| PRO | 9900 ₸ | 30 сек | Приоритет, «от хозяина», несколько районов |

## Установка

```bash
pip install -r requirements.txt
```

## Конфигурация (.env)

```
TOKEN=...
DATABASE_URL=postgresql://user:pass@host:5432/db
ADMIN_IDS=123456789
PAYMENT_CARD=0000 0000 0000 0000
PRICE_STANDARD=4900
PRICE_PRO=9900
PROXY_LIST=http://proxy1:8080,http://proxy2:8080
```

## Запуск

```bash
python main.py
```

## Railway

1. Добавьте PostgreSQL (Railway → New → Database)
2. Подключите репозиторий
3. Укажите переменные: TOKEN, DATABASE_URL, ADMIN_IDS
4. Deploy

## Структура

```
app/
├── config.py
├── database/
│   ├── connection.py
│   └── repositories.py
├── handlers/
│   ├── start.py
│   ├── flow.py          # аренда/продажа и выбор параметров
│   ├── menu.py          # навигация через инлайн-клавиатуру
│   ├── subscription.py
│   ├── stats.py
│   ├── notifications.py
│   └── admin.py
├── keyboards/
│   ├── reply.py
│   └── inline.py
├── middleware/
│   ├── database.py
│   └── subscription.py
└── services/
    ├── parser.py
    ├── queue.py
    └── monitor.py
```
