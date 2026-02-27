import os
import sys
import logging
from flask import Flask, request
import telegram

# Configurazione logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = "8785372321:AAGhzTMpd7rH6du_Ct2ClkAjNL2rjs9U9Tk"
bot = telegram.Bot(token=TOKEN)

@app.route('/')
def home():
    return "✅ Bot test attivo!"

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("📩 Webhook ricevuto")
    
    try:
        update_data = request.get_json(force=True)
        logger.info(f"Update: {update_data}")
        
        # Rispondi sempre "ok" a Telegram
        return "OK", 200
    except Exception as e:
        logger.error(f"Errore: {e}")
        return "OK", 200

@app.route('/test')
def test():
    """Testa la connessione a Telegram"""
    try:
        me = bot.get_me()
        return f"✅ Bot connesso: @{me.username}"
    except Exception as e:
        return f"❌ Errore: {e}"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Server su porta {port}")
    app.run(host="0.0.0.0", port=port)
