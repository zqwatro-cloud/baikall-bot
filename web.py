from flask import Flask
import threading
import os
import time
import requests
from bot import main

app = Flask(__name__)

@app.route('/')
def index():
    return "Baikall Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    main()

def keep_alive():
    """Каждые 10 минут пингуем себя, чтобы Render не засыпал"""
    url = f"https://baikall-bot.onrender.com/"
    while True:
        time.sleep(600)  # 10 минут
        try:
            requests.get(url, timeout=10)
            print("✅ Keep-alive ping sent")
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем keep-alive в отдельном потоке
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    # Запускаем Flask-сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)