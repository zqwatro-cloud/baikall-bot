import os
import threading
import asyncio
from flask import Flask
from bot import main as bot_main

app = Flask(__name__)

# Эндпоинт для проверки работоспособности (Render будет пинговать)
@app.route('/')
@app.route('/health')
def health_check():
    return 'Bot is running!', 200

# Функция для запуска бота в отдельном потоке
def run_bot():
    # Твой main() из bot.py использует asyncio, 
    # поэтому запускаем его правильно
    asyncio.run(bot_main())

if __name__ == '__main__':
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запускаем Flask-сервер на порту, который даст Render
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)