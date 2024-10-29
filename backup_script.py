import os
import time
import schedule
import telegram
import github
from github import Github
from datetime import datetime
from dotenv import load_dotenv
import shutil
import logging
import requests
import hashlib
import argparse
import asyncio

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='backup.log'
)

# Конфигурация из .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REPO_NAME = os.getenv('GITHUB_REPO_NAME')

def send_telegram_message(message):
    """Отправка сообщений в Telegram"""
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info("Telegram сообщение отправлено успешно")
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {str(e)}")

def check_github_token():
    """Проверка валидности GitHub токена"""
    try:
        g = Github(GITHUB_TOKEN)
        g.get_user().login
        return True
    except github.GithubException:
        send_telegram_message("⚠️ GitHub токен истёк! Необходимо обновить токен.")
        return False

def find_marzban_path():
    """Автоматический поиск пути к Marzban"""
    possible_paths = [
        "/opt/marzban",
        "/root/marzban",
        "/var/lib/marzban"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"Найден путь Marzban: {path}")
            return path
            
    logging.warning("Путь к Marzban не найден")
    return None

def find_amnezia_path():
    """Автоматический поиск пути к AmneziaVPN"""
    possible_paths = [
        "/opt/amnezia",
        "/var/lib/amnezia",
        "/root/amnezia"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"Найден путь AmneziaVPN: {path}")
            return path
            
    logging.warning("Путь к AmneziaVPN не найден")
    return None

def backup_marzban_mysql():
    """Бэкап MySQL базы Marzban"""
    try:
        if os.path.exists("/var/lib/marzban/mysql"):
            env_path = "/opt/marzban/.env"
            if os.path.exists(env_path):
                # Чтение пароля MySQL из .env файла
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('MYSQL_ROOT_PASSWORD='):
                            mysql_password = line.split('=')[1].strip()
                            break
                
                # Создание временной директории для бэкапа
                backup_dir = "/tmp/marzban_mysql_backup"
                os.makedirs(backup_dir, exist_ok=True)
                
                # Выполнение команды mysqldump через docker
                cmd = f"docker exec marzban-mysql-1 mysqldump -u root -p{mysql_password} --all-databases > {backup_dir}/all_databases.sql"
                os.system(cmd)
                
                return backup_dir
    except Exception as e:
        logging.error(f"Ошибка при бэкапе MySQL: {str(e)}")
    return None

def create_backup():
    """Создание бэкапа данных"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'backup_{timestamp}'
    
    try:
        os.makedirs(backup_dir)
        
        # Автоматический поиск путей
        marzban_path = find_marzban_path()
        amnezia_path = find_amnezia_path()
        
        # Бэкап Marzban
        if marzban_path:
            shutil.copytree(marzban_path, f'{backup_dir}/marzban')
            # Дополнительный бэкап MySQL если есть
            mysql_backup = backup_marzban_mysql()
            if mysql_backup:
                shutil.copytree(mysql_backup, f'{backup_dir}/marzban_mysql')
                shutil.rmtree(mysql_backup)
        
        # Бэкап AmneziaVPN
        if amnezia_path:
            shutil.copytree(amnezia_path, f'{backup_dir}/amnezia')
        
        # Если ни один путь не найден
        if not marzban_path and not amnezia_path:
            raise Exception("Не найдены пути к Marzban или AmneziaVPN")
        
        # Создаём архив
        archive_name = f'{backup_dir}.zip'
        shutil.make_archive(backup_dir, 'zip', backup_dir)
        
        return archive_name, backup_dir
    except Exception as e:
        logging.error(f"Ошибка создания бэкапа: {str(e)}")
        send_telegram_message(f"❌ Ошибка создания бэкапа: {str(e)}")
        return None, None

def ensure_github_repo_exists():
    """Проверка и создание приватного репозитория если он не существует"""
    try:
        g = Github(GITHUB_TOKEN)
        user = g.get_user()
        
        try:
            repo = user.get_repo(REPO_NAME)
            logging.info(f"Репозиторий {REPO_NAME} уже существует")
            return repo
        except github.GithubException as e:
            if e.status == 404:  # Репозиторий не найден
                logging.info(f"Создаём новый приватный репозиторий {REPO_NAME}")
                repo = user.create_repo(
                    name=REPO_NAME,
                    private=True,
                    description="Автоматические бэкапы Marzban и AmneziaVPN",
                    auto_init=True
                )
                
                # Создаём директорию backups
                try:
                    repo.create_file(
                        "backups/.gitkeep",
                        "Initial commit",
                        ""
                    )
                except github.GithubException:
                    pass  # Игнорируем если файл уже существует
                
                send_telegram_message(f"✅ Создан новый приватный репозиторий {REPO_NAME}")
                return repo
            else:
                raise
    except Exception as e:
        logging.error(f"Ошибка при проверке/создании репозитория: {str(e)}")
        send_telegram_message(f"❌ Ошибка при проверке/создании репозитория: {str(e)}")
        return None

def upload_to_github(archive_name):
    """Загрузка бэкапа на GitHub"""
    if not check_github_token():
        return False
        
    try:
        # Проверяем/создаём репозиторий
        repo = ensure_github_repo_exists()
        if not repo:
            return False
        
        # Создаём имя файла для GitHub
        file_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        # Загружаем файл
        with open(archive_name, 'rb') as file:
            content = file.read()
            repo.create_file(
                f"backups/{file_name}",
                f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                content
            )
        
        # Проверяем размер репозитория
        repo_size = repo.size / 1024  # Размер в МБ
        if repo_size > 900:  # Если близко к лимиту в 1GB
            send_telegram_message(f"⚠️ Репозиторий занимает {repo_size:.2f}MB. Рекомендуется очистка.")
            
        return True
    except Exception as e:
        logging.error(f"Ошибка загрузки на GitHub: {str(e)}")
        send_telegram_message(f"❌ Ошибка загрузки на GitHub: {str(e)}")
        return False

def cleanup(backup_dir, archive_name):
    """Очистка временных файлов"""
    try:
        shutil.rmtree(backup_dir)
        os.remove(archive_name)
    except Exception as e:
        logging.error(f"Ошибка очистки временных файлов: {str(e)}")

def backup_job():
    """Основная функция бэкапа"""
    logging.info("Начало процесса бэкапа")
    send_telegram_message("🔄 Начало создания бэкапа...")
    
    archive_name, backup_dir = create_backup()
    if archive_name and backup_dir:
        if upload_to_github(archive_name):
            send_telegram_message("✅ Бэкап успешно создан и загружен на GitHub")
        cleanup(backup_dir, archive_name)
    
    logging.info("Процесс бэкапа завершён")

async def get_chat_id():
    """Получение TELEGRAM_CHAT_ID"""
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Очищаем предыдущие обновления
        await bot.delete_webhook(drop_pending_updates=True)
        
        print("👋 Отправьте любое сообщение боту для получения chat_id")
        
        while True:
            try:
                updates = await bot.get_updates(timeout=30, offset=-1, limit=1)
                if updates:
                    chat_id = updates[0].message.chat.id
                    print(f"\n✅ Ваш TELEGRAM_CHAT_ID: {chat_id}")
                    print(f"Добавьте его в .env файл как TELEGRAM_CHAT_ID={chat_id}")
                    return chat_id
                await asyncio.sleep(1)
            except telegram.error.TimedOut:
                continue
            except telegram.error.RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Exception as e:
                print(f"❌ Ошибка получения chat_id: {str(e)}")
                logging.error(f"Ошибка получения chat_id: {str(e)}")
                return None
                
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {str(e)}")
        logging.error(f"Ошибка инициализации бота: {str(e)}")
        return None

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Скрипт для бэкапа Marzban и AmneziaVPN')
    parser.add_argument('--init-repo', action='store_true', 
                       help='Только создать GitHub репозиторий без запуска бэкапа')
    parser.add_argument('--get-chat-id', action='store_true',
                       help='Получить TELEGRAM_CHAT_ID')
    return parser.parse_args()

def init_repository():
    """Инициализация репозитория"""
    logging.info("Начало инициализации репозитория")
    send_telegram_message("🔄 Начало создания репозитория...")
    
    repo = ensure_github_repo_exists()
    if repo:
        send_telegram_message("✅ Репозиторий успешно создан/проверен")
        logging.info("Репозиторий успешно инициализирован")
        
        # Планируем первый бэкап через минуту
        schedule.every(1).minutes.do(first_backup).tag('first_backup')
        while True:
            schedule.run_pending()
            time.sleep(1)
            # Проверяем, выполнен ли первый бэкап
            if not schedule.get_jobs('first_backup'):
                break
        return True
    return False

def first_backup():
    """Выполнение первого бэкапа"""
    backup_job()
    # Удаляем задачу первого бэкапа после выполнения
    schedule.clear('first_backup')

def main():
    """Основная функция"""
    args = parse_arguments()
    
    logging.info("Запуск скрипта")
    
    if args.get_chat_id:
        if not TELEGRAM_BOT_TOKEN:
            print("❌ Установите TELEGRAM_BOT_TOKEN в .env файле")
            return
        asyncio.run(get_chat_id())
        return
        
    if args.init_repo:
        if not all([GITHUB_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REPO_NAME]):
            print("❌ Заполните все необходимые переменные в .env файле:")
            print("GITHUB_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_REPO_NAME")
            return
        init_repository()
        return
        
    if not all([GITHUB_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REPO_NAME]):
        print("❌ Заполните все необходимые переменные в .env файле:")
        print("GITHUB_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_REPO_NAME")
        return
        
    send_telegram_message("🚀 Скрипт бэкапа запущен")
    
    if not ensure_github_repo_exists():
        send_telegram_message("❌ Не удалось создать/проверить репозиторий. Проверьте GitHub токен.")
        return
    
    schedule.every().hour.do(backup_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 