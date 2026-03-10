from flask import Flask, request, jsonify
import telebot
from telebot import types
import logging
import json
import os
import threading
import time
import requests
from config import BOT_TOKEN, ADMIN_IDS, PRODUCT_URL, PORT, logger, validate_config, WEBHOOK_SECRET

# ======================== ИНИЦИАЛИЗАЦИЯ ========================

# Проверяем конфигурацию перед запуском
if not validate_config():
    exit(1)

# Глобальная переменная для хранения текущего URL (для тестов)
# В продакшене он будет известен заранее
PUBLIC_URL = None

# Создаем бота и сервер
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


# ======================== TELEGRAM ЧАСТЬ ========================

def notify_admins(text, parse_mode=None):
    """Отправляет уведомление всем администраторам"""
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")


@bot.message_handler(commands=['start'])
def start(message):
    """Отправляем ссылку на товар"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛒 Перейти к оплате", url=PRODUCT_URL))

    bot.send_message(
        message.chat.id,
        "👋 *Добро пожаловать в магазин!*\n\n"
        "💰 *Товар:* Премиум доступ\n"
        "💳 *Цена:* указана на странице оплаты\n\n"
        "👇 Нажми кнопку для перехода к оплате:",
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.message_handler(commands=['id'])
def get_id(message):
    """Узнать свой Telegram ID"""
    bot.send_message(
        message.chat.id,
        f"🆔 Твой Telegram ID: `{message.chat.id}`",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['admin'])
def admin_help(message):
    """Помощь для администраторов"""
    if message.chat.id in ADMIN_IDS:
        bot.send_message(
            message.chat.id,
            "👑 *Админ-панель*\n\n"
            "Доступные команды:\n"
            "/seturl <url> - установить публичный URL (для тестов)\n"
            "/status - проверить статус сервера\n"
            "/testwebhook - отправить тестовый вебхук",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❌ У тебя нет прав администратора.")


@bot.message_handler(commands=['seturl'])
def set_url(message):
    """Установить публичный URL (для тестов)"""
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Только для администраторов")
        return

    global PUBLIC_URL
    parts = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message, "❌ Использование: /seturl https://your-domain.com")
        return

    PUBLIC_URL = parts[1].rstrip('/')
    bot.reply_to(message, f"✅ URL установлен: {PUBLIC_URL}\n\n"
                          f"В продакшене (Railway) URL будет постоянным.")


@bot.message_handler(commands=['status'])
def status(message):
    """Проверить статус сервера (только для админов)"""
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Только для администраторов")
        return

    status_msg = f"📊 *Статус сервера*\n\n"
    status_msg += f"🔗 Товар: {PRODUCT_URL}\n"
    status_msg += f"🌐 Публичный URL: {PUBLIC_URL or 'не установлен'}\n"
    status_msg += f"👑 Админы: {len(ADMIN_IDS)}\n"
    status_msg += f"🖥 Режим: {'Railway' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Локальный'}\n"

    # Проверяем доступность вебхука
    if PUBLIC_URL:
        try:
            response = requests.get(f"{PUBLIC_URL}", timeout=5)
            status_msg += f"✅ Сервер доступен (статус: {response.status_code})"
        except Exception as e:
            status_msg += f"❌ Сервер недоступен: {str(e)[:50]}"

    bot.reply_to(message, status_msg, parse_mode="Markdown")


@bot.message_handler(commands=['testwebhook'])
def test_webhook_command(message):
    """Отправить тестовый вебхук (только для админов)"""

    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Только для администраторов")
        return

    if not PUBLIC_URL:
        bot.reply_to(message, "❌ Сначала установи URL через /seturl")
        return

    # Создаем тестовые данные
    test_data = {
        "id": "test_" + str(int(time.time())),
        "amount": 100,
        "currency": "RUB",
        "status": "success",
        "orderId": "order_" + str(int(time.time())),
        "email": f"test_{message.chat.id}@example.com",
        "product": "Тестовый товар",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        webhook_url = f"{PUBLIC_URL}/webhook/lava"

        bot.reply_to(message, f"🔄 Отправляю тестовый вебхук на {webhook_url}...")

        response = requests.post(
            webhook_url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            bot.reply_to(
                message,
                f"✅ Тестовый вебхук отправлен!\n\n"
                f"*Отправленные данные:*\n```\n{json.dumps(test_data, indent=2)}\n```",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(
                message,
                f"❌ Ошибка: статус {response.status_code}\n{response.text[:200]}"
            )

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")


@bot.message_handler(commands=['help'])
def help_command(message):
    """Общая справка"""
    help_text = (
        "📚 *Доступные команды*\n\n"
        "👤 *Для всех:*\n"
        "/start - Получить ссылку на товар\n"
        "/id - Узнать свой Telegram ID\n"
        "/help - Эта справка\n\n"
    )

    if message.chat.id in ADMIN_IDS:
        help_text += (
            "👑 *Для администраторов:*\n"
            "/seturl <url> - Установить публичный URL\n"
            "/status - Статус сервера\n"
            "/testwebhook - Тестовый вебхук\n"
            "/admin - Админ-панель"
        )

    bot.reply_to(message, help_text, parse_mode="Markdown")


# ======================== WEBHOOK ЧАСТЬ ========================

@app.route('/', methods=['GET'])
def index():
    """Проверка работы сервера"""
    return jsonify({
        "status": "ok",
        "message": "Bot is running!",
        "environment": "Railway" if os.environ.get('RAILWAY_ENVIRONMENT') else "Local",
        "endpoints": {
            "webhook": "/webhook/lava",
            "test": "/webhook/test"
        },
        "admins": len(ADMIN_IDS)
    })


@bot.message_handler(commands=['testwebhook'])
def test_webhook_command(message):
    """Отправить тестовый вебхук (только для админов)"""

    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Только для администраторов")
        return

    if not PUBLIC_URL:
        bot.reply_to(message, "❌ Сначала установи URL через /seturl")
        return

    # Получаем секретный ключ из окружения
    webhook_secret = os.getenv('WEBHOOK_SECRET')
    if not webhook_secret:
        bot.reply_to(message, "❌ WEBHOOK_SECRET не настроен в окружении")
        return

    # Создаем тестовые данные
    test_data = {
        "id": "test_" + str(int(time.time())),
        "amount": 100,
        "currency": "RUB",
        "status": "success",
        "orderId": "order_" + str(int(time.time())),
        "email": f"test_{message.chat.id}@example.com",
        "product": "Тестовый товар",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "customData": {
            "telegram_id": message.chat.id,
            "username": message.from_user.username
        }
    }

    try:
        webhook_url = f"{PUBLIC_URL}/webhook/lava"

        bot.reply_to(message, f"🔄 Отправляю тестовый вебхук на {webhook_url}...")

        # ВАЖНО: Добавляем ключ в заголовок
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": webhook_secret  # Ключ для авторизации
        }

        response = requests.post(
            webhook_url,
            json=test_data,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            bot.reply_to(
                message,
                f"✅ Тестовый вебхук отправлен!\n\n"
                f"*Отправленные данные:*\n```\n{json.dumps(test_data, indent=2, ensure_ascii=False)}\n```",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(
                message,
                f"❌ Ошибка: статус {response.status_code}\n{response.text[:200]}"
            )

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")


@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Для тестирования webhook"""
    data = request.json
    logger.info(f"🧪 Тестовый webhook: {data}")

    test_msg = f"🧪 *ТЕСТОВЫЙ WEBHOOK*\n\n```\n{json.dumps(data, indent=2)}\n```"
    notify_admins(test_msg, parse_mode="Markdown")

    return jsonify({"status": "test ok"}), 200


# ======================== ЗАПУСК ========================

def run_flask():
    """Запуск Flask сервера"""
    logger.info(f"🌐 Запуск Flask сервера на порту {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)


def run_bot():
    """Запуск бота"""
    logger.info("🤖 Telegram бот запущен")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")
        time.sleep(5)
        run_bot()  # Перезапуск при ошибке


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК БОТА ДЛЯ LAVA.TOP")
    print("=" * 60)
    print(f"\n📋 Информация:")
    print(f"   👑 Администраторов: {len(ADMIN_IDS)}")
    print(f"   🔗 Товар: {PRODUCT_URL}")
    print(f"   🌐 Порт: {PORT}")
    print(f"   🖥 Режим: {'Railway' if os.environ.get('RAILWAY_ENVIRONMENT') else 'Локальный'}")
    print("\n" + "=" * 60 + "\n")

    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Запускаем бота в главном потоке
    run_bot()