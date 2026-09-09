from flask import Flask
import threading
import os
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

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)