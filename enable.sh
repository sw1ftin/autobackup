#!/bin/bash

# Проверка на root права
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

# Установка Python и pip если их нет
if ! command -v python3 &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip
fi

# Создание директории для сервиса
mkdir -p /opt/backup-service
chmod 755 /opt/backup-service

# Создание виртуального окружения
python3 -m venv /opt/backup-service/venv
source /opt/backup-service/venv/bin/activate

# Копирование файлов
cp backup_script.py /opt/backup-service/
cp requirements.txt /opt/backup-service/
cp .env /opt/backup-service/
chmod 600 /opt/backup-service/.env

# Установка зависимостей
pip install -r /opt/backup-service/requirements.txt

# Создание директории для логов
mkdir -p /var/log/backup-service
chown $SUDO_USER:$SUDO_USER /var/log/backup-service

# Создание systemd сервиса
cat > /etc/systemd/system/backup-service.service << EOL
[Unit]
Description=Backup Service for Marzban and AmneziaVPN
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=/opt/backup-service
Environment=PATH=/opt/backup-service/venv/bin:$PATH
ExecStart=/opt/backup-service/venv/bin/python3 backup_script.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/backup-service/output.log
StandardError=append:/var/log/backup-service/error.log

[Install]
WantedBy=multi-user.target
EOL

# Перезагрузка демона systemd
systemctl daemon-reload

# Включение и запуск сервиса
systemctl enable backup-service
systemctl start backup-service

echo "✅ Сервис успешно установлен и запущен!"
echo "📝 Логи доступны в /var/log/backup-service/"
echo "💡 Статус сервиса можно проверить командой: systemctl status backup-service" 