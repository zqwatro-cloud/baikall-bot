from flask import Flask
import threading
import os
import time
import requests
import logging
from bot import main

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return "Baikall Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Запускает бота с обработкой ошибок"""
    try:
        logger.info("🚀 Starting bot...")
        main()
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()

def keep_alive():
    """Каждые 10 минут пингуем себя, чтобы Render не засыпал"""
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'baikall-bot.onrender.com')}/"
    while True:
        time.sleep(600)  # 10 минут
        try:
            requests.get(url, timeout=5)
            logger.info("✅ Keep-alive ping sent")
        except Exception as e:
            logger.error(f"❌ Keep-alive error: {e}")

if __name__ == '__main__':
    logger.info("🔧 Starting Flask server...")
    
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("🤖 Bot thread started")
    
    # Запускаем keep-alive в фоновом потоке
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("🔄 Keep-alive thread started")
    
    # Запускаем Flask-сервер
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Flask server starting on port {port}")
    app.run(host='0.0.0.0', port=port)