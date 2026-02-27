import os
import sys
import logging
import asyncio
import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# CONFIGURAZIONE LOGGING MASSIMA
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# STAMP SUBITO PER DEBUG
print(f"""
🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
NUOVA VERSIONE MAIN.PY ESEGUITA: {datetime.datetime.now()}
🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
""", flush=True)

app = Flask(__name__)

# TOKEN
TOKEN = "8785372321:AAGhzTMpd7rH6du_Ct2ClkAjNL2rjs9U9Tk"

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
bot_app = None

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

async def setup_bot():
    global bot_app
    bot_app = Application.builder().token(TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(menu_farmaci, pattern="^menu_farmaci$"))
    bot_app.add_handler(CallbackQueryHandler(menu_principale, pattern="^menu_principale$"))
    bot_app.add_handler(CallbackQueryHandler(menu_dosaggio, pattern="^farmaco_"))
    bot_app.add_handler(CallbackQueryHandler(menu_categoria_blocco, pattern="^dosaggio_"))
    bot_app.add_handler(CallbackQueryHandler(menu_blocchi, pattern="^cat_"))
    bot_app.add_handler(CallbackQueryHandler(mostra_raccomandazione, pattern="^blocco_"))
    
    await bot_app.initialize()
    await bot_app.start()
    logger.info("✅ Bot Telegram avviato")
    return bot_app

@app.route('/')
def home():
    return "Bot Anticoagulanti & Anestesia attivo! Cerca su Telegram: @AnticoagulantiEanestesiabot"

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("🔵 WEBHOOK CHIAMATO")
    if bot_app and request.is_json:
        try:
            update_data = request.get_json(force=True)
            logger.info(f"📩 Update ID: {update_data.get('update_id')}")
            
            update = Update.de_json(update_data, bot_app.bot)
            
            if bot_app.loop and bot_app.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    bot_app.process_update(update),
                    bot_app.loop
                )
                future.result(timeout=5)
                logger.info("✅ Update processato")
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_app.process_update(update))
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Errore: {e}", exc_info=True)
    
    return "OK", 200

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Avvia bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_bot())
    
    logger.info(f"🚀 Server su porta {port}")
    app.run(host="0.0.0.0", port=port)
