#!/bin/bash

# Проверка на root права
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Остановка и отключение сервиса
systemctl stop backup-service
systemctl disable backup-service

# Удаление файлов сервиса
rm -f /etc/systemd/system/backup-service.service
rm -rf /opt/backup-service

# Очистка логов
rm -rf /var/log/backup-service

# Перезагрузка демона systemd
systemctl daemon-reload
systemctl reset-failed

echo "✅ Сервис успешно остановлен и удален!" 