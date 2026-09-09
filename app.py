import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from bot import start, button_handler, text_handler, pre_checkout_handler, successful_payment_handler

# ========== НАСТРОЙКА ==========
BOT_TOKEN = "8752748803:AAFjS-NPp5Tard5EORpZm0u-eZYxHstIswI"
WEBHOOK_URL = "https://baikall-bot.onrender.com"  # ← ЗАМЕНИ НА СВОЙ URL

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Создаём приложение бота
bot_app = Application.builder().token(BOT_TOKEN).build()

# Регистрируем обработчики
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
bot_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

# Эндпоинт для проверки работоспособности
@app.route('/')
@app.route('/health')
def health_check():
    return 'Bot is running!', 200

# Webhook эндпоинт — сюда Telegram будет присылать обновления
@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        await bot_app.process_update(update)
        return 'OK', 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return 'Error', 500

# Настройка webhook при запуске
@app.before_first_request
def setup_webhook():
    webhook_url = f"{WEBHOOK_URL}/webhook"
    bot_app.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to: {webhook_url}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)