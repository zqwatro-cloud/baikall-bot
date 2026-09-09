import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from bot import start, button_handler, text_handler, pre_checkout_handler, successful_payment_handler

BOT_TOKEN = "8752748803:AAFjS-NPp5Tard5EORpZm0u-eZYxHstIswI"
WEBHOOK_URL = "https://baikall-bot.onrender.com"

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_handler))
dispatcher.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
dispatcher.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

@app.route('/')
@app.route('/health')
def health():
    return 'OK', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return 'OK', 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return 'Error', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)