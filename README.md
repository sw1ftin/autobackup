# Marzban & AmneziaVPN Backup Script

Автоматическое резервное копирование Marzban и AmneziaVPN на GitHub с уведомлениями в Telegram.

## Установка

1. Клонируйте репозиторий
2. Создайте `.env`:
```bash
git clone https://github.com/your-username/backup-script.git
cd backup-script
```

2. Создайте файл .env с необходимыми переменными:
```plaintext
GITHUB_TOKEN=your_github_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GITHUB_REPO_NAME=your_repo_name
```

3. Установите сервис:
```bash
sudo ./enable.sh
```

## Использование

Получить TELEGRAM_CHAT_ID:
```bash
python backup_script.py --get-chat-id
```

Создать GitHub репозиторий:
```bash
python backup_script.py --init-repo
```

Удалить сервис:
```bash
sudo ./disable.sh
```

## Возможности

- Автопоиск Marzban и AmneziaVPN
- Бэкап MySQL базы Marzban
- Приватный GitHub репозиторий
- Telegram уведомления
- Мониторинг размера репозитория
- Systemd сервис
- Подробное логирование

## Требования

- Python 3.7+
- Docker (для MySQL)
- GitHub токен
- Telegram бот

## Логи

```bash
tail -f /var/log/backup-service/output.log
```

## Лицензия

MIT