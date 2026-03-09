import os
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot
BOT_TOKEN = '8309619483:AAHcEzTqeHQZRVuRIk-0z0qL2HJETA24wkg'

# Твои ID администраторов (кому приходят уведомления)
ADMIN_IDS = [8214136791, 1441402891]

# URL товара в Lava.top
PRODUCT_URL = "https://app.lava.top/products/77a5bd8f-7e4c-41e1-9a0f-42e9cc915fdf/345102f6-2fce-4311-a321-d241b10f49af?currency=RUB"

# Настройки сервера (Railway сам назначает порт)
PORT = 5000

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_config():
    """Проверка наличия обязательных переменных"""
    required_vars = {
        'BOT_TOKEN': BOT_TOKEN,
        'ADMIN_IDS': ADMIN_IDS,
        'PRODUCT_URL': PRODUCT_URL
    }

    missing = [var for var, value in required_vars.items() if not value]

    if missing:
        logger.error(f"❌ Отсутствуют обязательные переменные: {', '.join(missing)}")
        logger.error("Скопируйте .env.example в .env и заполните своими данными")
        return False

    logger.info(f"✅ Конфигурация загружена. Администраторов: {len(ADMIN_IDS)}")
    return True