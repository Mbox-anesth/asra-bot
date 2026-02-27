import os
import sys
import logging
import asyncio
import time
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# TOKEN
TOKEN = "8785372321:AAGhzTMpd7rH6du_Ct2ClkAjNL2rjs9U9Tk"
bot = Bot(token=TOKEN)

# Loop asincrono globale
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Variabili globali
application = None
bot_ready = False

# DATI LINEE GUIDA ASRA
FARMACI = {
    "apixaban": {"nome": "Apixaban", "categoria": "DOACs"},
    "rivaroxaban": {"nome": "Rivaroxaban", "categoria": "DOACs"},
    "dabigatran": {"nome": "Dabigatran", "categoria": "DOACs"},
    "warfarin": {"nome": "Warfarin", "categoria": "Antagonisti Vitamina K"},
    "clopidogrel": {"nome": "Clopidogrel", "categoria": "Antipiastrinici"},
    "prasugrel": {"nome": "Prasugrel", "categoria": "Antipiastrinici"},
    "ticagrelor": {"nome": "Ticagrelor", "categoria": "Antipiastrinici"},
    "ufh_iv": {"nome": "UFH endovena", "categoria": "Eparine"},
    "ufh_sc_bassa": {"nome": "UFH sottocute (bassa dose)", "categoria": "Eparine"},
    "lmwh_bassa": {"nome": "LMWH bassa dose", "categoria": "Eparine"},
    "lmwh_alta": {"nome": "LMWH alta dose", "categoria": "Eparine"},
    "fondaparinux": {"nome": "Fondaparinux", "categoria": "Altri"},
    "aspirina": {"nome": "Aspirina/FANS", "categoria": "Antipiastrinici"},
}

LINEE_GUIDA = {
    ("apixaban", "alta"): {
        "sospensione": "≥ 72 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 24h dopo rimozione catetere",
        "warning": "• Target accettabile: <30 ng/mL o aXa ≤0.1 IU/mL\n• Considerare test anti-Xa se <72h"
    },
    ("apixaban", "bassa"): {
        "sospensione": "≥ 36 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 6h dopo posizionamento/rimozione",
        "warning": "• Target accettabile: <30 ng/mL o aXa ≤0.1 IU/mL"
    },
    ("rivaroxaban", "alta"): {
        "sospensione": "≥ 72 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 24h dopo rimozione catetere",
        "warning": "• Target accettabile: <30 ng/mL o aXa ≤0.1 IU/mL"
    },
    ("rivaroxaban", "bassa"): {
        "sospensione": "≥ 24 ore (≥30h se CrCl<30)",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 6h dopo posizionamento/rimozione",
        "warning": "• Target accettabile: <30 ng/mL o aXa ≤0.1 IU/mL"
    },
    ("dabigatran", "alta"): {
        "sospensione": "≥ 72 ore (120h se CrCl 30-49)",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 24h dopo rimozione catetere",
        "warning": "• Evitare se CrCl<30\n• Target accettabile: <30 ng/mL"
    },
    ("dabigatran", "bassa"): {
        "sospensione": "≥ 48 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥ 6h dopo posizionamento/rimozione",
        "warning": "• Target accettabile: <30 ng/mL"
    },
    ("warfarin", None): {
        "sospensione": "≥ 5 giorni",
        "riferimento": "Ultima dose",
        "prima_dose": "INR <1.5 per rimozione catetere",
        "warning": "• Monitorare INR daily\n• Rimuovere catetere se INR <1.5"
    },
    ("clopidogrel", None): {
        "sospensione": "5-7 giorni",
        "riferimento": "Ultima dose",
        "prima_dose": "Immediatamente dopo (senza dose di carico)",
        "warning": "• Cateteri possono essere mantenuti 1-2 giorni"
    },
    ("prasugrel", None): {
        "sospensione": "7-10 giorni",
        "riferimento": "Ultima dose",
        "prima_dose": "Immediatamente dopo (senza dose di carico)",
        "warning": "• Cateteri NON devono essere mantenuti"
    },
    ("ticagrelor", None): {
        "sospensione": "5 giorni",
        "riferimento": "Ultima dose",
        "prima_dose": "Immediatamente dopo (senza dose di carico)",
        "warning": "• Cateteri NON devono essere mantenuti"
    },
    ("ufh_iv", None): {
        "sospensione": "Sospendere infusione 4-6h prima",
        "riferimento": "Ultima dose",
        "prima_dose": "1h dopo procedura",
        "warning": "• Valutare stato coagulazione (aPTT) e normalizzarlo prima della procedura"
    },
    ("ufh_sc_bassa", None): {
        "sospensione": "≥ 4-6 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "Immediatamente dopo rimozione catetere",
        "warning": "• Si possono mantenere cateteri. Rimuovere ≥4-6h dopo ultima dose"
    },
    ("lmwh_bassa", None): {
        "sospensione": "≥ 12 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "Singola/die: 12h dopo. Due volte/die: giorno dopo",
        "warning": "• Considerare test aXa se <12h. Target aXa ≤0.1 IU/mL"
    },
    ("lmwh_alta", None): {
        "sospensione": "≥ 24 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥24h dopo intervento ad alto rischio",
        "warning": "• Considerare test aXa se <24h. Target aXa ≤0.1 IU/mL"
    },
    ("fondaparinux", "bassa"): {
        "sospensione": "36-42 ore",
        "riferimento": "Ultima dose",
        "prima_dose": "≥6h dopo rimozione catetere",
        "warning": "• Considerare test aXa (calibrato). Target aXa ≤0.1 IU/mL"
    },
    ("aspirina", None): {
        "sospensione": "Nessuna specifica",
        "riferimento": "-",
        "prima_dose": "-",
        "warning": "• Gli NSAIDs non rappresentano un rischio aggiuntivo significativo"
    },
}

BLOCCHI = {
    "superficiali": [
        "Sottotenoniano", "PECS I", "PECS II", "Serratus block", 
        "Fascia iliaca", "Safeno (canale adduttorio)", "Blocchi terminali distali",
        "TAP block", "Rectus sheath"
    ],
    "profondi": [
        "Retrobulbare", "Peribulbare", "PENG block", "Plesso lombare (psoas)",
        "Paravertebrale", "Sciatico prossimale", "Interscalenico", 
        "Sovraclaveare", "Infraclavicolare"
    ],
    "dipendenti": [
        "Erector Spinae Plane", "Quadratus Lumborum", "Varianti profonde PECS"
    ]
}

user_state = {}

# HANDLER TELEGRAM
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"✅ /start ricevuto da user {update.effective_user.id}")
    keyboard = [[InlineKeyboardButton("💊 Seleziona Farmaco", callback_data="menu_farmaci")]]
    await update.message.reply_text(
        "👋 **Anticoagulanti & Anestesia** - Linee Guida ASRA 5a edizione (2025)\n\n"
        "Questo bot fornisce le raccomandazioni per blocchi regionali "
        "in pazienti in terapia antitrombotica.\n\n"
        "Seleziona un'opzione:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    logger.info(f"✅ Risposta inviata a user {update.effective_user.id}")

async def menu_farmaci(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for farmaco_id, info in FARMACI.items():
        keyboard.append([InlineKeyboardButton(info["nome"], callback_data=f"farmaco_{farmaco_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="menu_principale")])
    await query.edit_message_text(
        "💊 **Seleziona il farmaco:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def menu_dosaggio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    farmaco_id = query.data.replace("farmaco_", "")
    user_state[query.from_user.id] = {"farmaco": farmaco_id}
    
    if farmaco_id in ["apixaban", "rivaroxaban", "dabigatran", "fondaparinux"]:
        keyboard = [
            [InlineKeyboardButton("💉 Alta dose", callback_data=f"dosaggio_{farmaco_id}_alta")],
            [InlineKeyboardButton("💊 Bassa dose", callback_data=f"dosaggio_{farmaco_id}_bassa")],
            [InlineKeyboardButton("🔙 Indietro", callback_data="menu_farmaci")]
        ]
        await query.edit_message_text(
            "📊 **Seleziona il dosaggio:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await menu_categoria_blocco(update, context, farmaco_id, None)

async def menu_categoria_blocco(update: Update, context: ContextTypes.DEFAULT_TYPE, farmaco_id=None, dosaggio=None):
    query = update.callback_query
    if query:
        await query.answer()
        if hasattr(query, 'data') and query.data.startswith("dosaggio_"):
            parts = query.data.split("_")
            farmaco_id = parts[1]
            dosaggio = parts[2]
            user_state[query.from_user.id] = {"farmaco": farmaco_id, "dosaggio": dosaggio}
        edit_func = query.edit_message_text
    else:
        edit_func = update.message.reply_text
    
    keyboard = [
        [InlineKeyboardButton("🔹 Blocchi Superficiali", callback_data=f"cat_superficiali_{farmaco_id}_{dosaggio or 'None'}")],
        [InlineKeyboardButton("🔺 Blocchi Profondi", callback_data=f"cat_profondi_{farmaco_id}_{dosaggio or 'None'}")],
        [InlineKeyboardButton("⚙️ Dipendenti dalla tecnica", callback_data=f"cat_dipendenti_{farmaco_id}_{dosaggio or 'None'}")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="menu_farmaci")]
    ]
    
    await edit_func(
        "📌 **Seleziona la categoria del blocco:**\n\n"
        "_Tooltip: La classificazione riflette il rischio anatomico emorragico_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def menu_blocchi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    cat = parts[1]
    farmaco_id = parts[2]
    dosaggio = parts[3] if parts[3] != "None" else None
    
    blocchi_lista = BLOCCHI[cat]
    keyboard = []
    for blocco in blocchi_lista:
        keyboard.append([InlineKeyboardButton(blocco, callback_data=f"blocco_{cat}_{blocco}_{farmaco_id}_{dosaggio}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Indietro", callback_data="menu_categoria_blocco")])
    
    tooltips = {
        "superficiali": "🔹 Rischio emorragico minore",
        "profondi": "🔺 Rischio emorragico maggiore (spazi non comprimibili)",
        "dipendenti": "⚙️ Rischio variabile in base alla tecnica"
    }
    
    await query.edit_message_text(
        f"{tooltips[cat]}\n\n**Blocchi disponibili:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def mostra_raccomandazione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    cat = parts[1]
    blocco = parts[2]
    farmaco_id = parts[3]
    dosaggio = parts[4] if parts[4] != "None" else None
    
    linea = LINEE_GUIDA.get((farmaco_id, dosaggio))
    if not linea and dosaggio:
        linea = LINEE_GUIDA.get((farmaco_id, None))
    
    if not linea:
        await query.edit_message_text(
            "❌ **Nessuna raccomandazione specifica trovata**\n\n"
            "Consulta le linee guida originali.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Nuova ricerca", callback_data="menu_farmaci")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    farmaco_nome = FARMACI[farmaco_id]["nome"]
    messaggio = f"""💊 **Farmaco:** {farmaco_nome}
📊 **Dosaggio:** {dosaggio or 'N/A'}
🩺 **Blocco:** {blocco}
📌 **Categoria:** {cat}

⏳ **Tempo sospensione:** {linea['sospensione']}
🕒 **Riferimento temporale:** {linea['riferimento']}
📅 **Prima dose post-operatoria:** {linea['prima_dose']}

⚠️ **Warning ASRA / Note:**
{linea['warning']}

📖 *Linee Guida ASRA 5a edizione (2025)*"""
    
    keyboard = [[InlineKeyboardButton("🔄 Nuova ricerca", callback_data="menu_farmaci")]]
    await query.edit_message_text(
        messaggio, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def menu_principale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("💊 Seleziona Farmaco", callback_data="menu_farmaci")]]
    await query.edit_message_text(
        "🏠 **Menu Principale**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risponde a qualsiasi messaggio non gestito"""
    logger.info(f"📨 Echo handler: {update.message.text}")
    await update.message.reply_text(f"Hai scritto: {update.message.text}")
    logger.info(f"✅ Echo risposta inviata")

async def setup_application():
    """Setup dell'applicazione Telegram"""
    global application
    builder = Application.builder().token(TOKEN)
    builder.updater(None)
    application = builder.build()
    
    # Aggiungi handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu_farmaci, pattern="^menu_farmaci$"))
    application.add_handler(CallbackQueryHandler(menu_principale, pattern="^menu_principale$"))
    application.add_handler(CallbackQueryHandler(menu_dosaggio, pattern="^farmaco_"))
    application.add_handler(CallbackQueryHandler(menu_categoria_blocco, pattern="^dosaggio_"))
    application.add_handler(CallbackQueryHandler(menu_blocchi, pattern="^cat_"))
    application.add_handler(CallbackQueryHandler(mostra_raccomandazione, pattern="^blocco_"))
    
    # Handler echo per messaggi non gestiti
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_all))
    
    await application.initialize()
    await application.start()
    logger.info("✅ Application Telegram pronta")
    return application

# Avvia l'applicazione all'avvio
logger.info("🔄 Inizializzazione Application Telegram...")
application = loop.run_until_complete(setup_application())

# Avvia un thread per mantenere il loop in esecuzione
def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

thread = threading.Thread(target=run_loop, daemon=True)
thread.start()
logger.info("✅ Loop asincrono avviato in thread separato")

bot_ready = True
logger.info("✅ Bot completamente pronto!")

# FLASK ENDPOINTS
@app.route('/')
def home():
    return "✅ Bot Anticoagulanti & Anestesia attivo! Cerca su Telegram: @AnticoagulantiEanestesiabot"

@app.route('/webhook', methods=['POST'])
def webhook():
    # Logging MOLTO esplicito
    logger.info("="*50)
    logger.info("🔵 FUNZIONE WEBHOOK CHIAMATA - INIZIO")
    logger.info(f"🔵 Metodo richiesta: {request.method}")
    logger.info(f"🔵 Headers: {dict(request.headers)}")
    
    if not application:
        logger.error("❌ Application non inizializzata")
        return "OK", 200
    
    try:
        # Verifica che sia una richiesta JSON
        if not request.is_json:
            logger.error(f"❌ Richiesta non JSON: {request.data}")
            return "OK", 200
            
        update_data = request.get_json(force=True)
        logger.info(f"📩 Update ricevuto - ID: {update_data.get('update_id')}")
        
        if 'message' in update_data:
            logger.info(f"📨 Messaggio: {update_data['message'].get('text')}")
        
        update = Update.de_json(update_data, bot)
        
        # Processa l'update in modo NON bloccante
        asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            loop
        )
        logger.info("✅ Update inviato per processing (asincrono)")
        
    except Exception as e:
        logger.error(f"❌ Errore nel webhook: {e}", exc_info=True)
    
    logger.info("🔵 FUNZIONE WEBHOOK CHIAMATA - FINE")
    logger.info("="*50)
    return "OK", 200

@app.route('/test')
def test():
    """Test connessione Telegram"""
    try:
        me = loop.run_until_complete(bot.get_me())
        return f"✅ Bot connesso: @{me.username}"
    except Exception as e:
        return f"❌ Errore: {e}"

@app.route('/health')
def health():
    status = "ready" if bot_ready else "starting"
    return f"Bot status: {status}", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Avvio server Flask sulla porta {port}")
    app.run(host="0.0.0.0", port=port)
