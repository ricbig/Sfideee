"""Configurazione del bot: orari, fuso orario, gioco e negozio.
Modifica qui i valori per personalizzare tutto."""

from zoneinfo import ZoneInfo

# Fuso orario usato per decidere QUANDO fare le azioni (le Actions girano in UTC)
TIMEZONE = ZoneInfo("Europe/Rome")

# --- Orari (ora locale italiana) ---
DAILY_HOUR = 10          # ora in cui arriva la sfida del giorno
REMINDER_HOUR = 15       # promemoria privato se la sfida non è ancora fatta
ADD_REMINDER_HOUR = 11   # ora del promemoria "aggiungete nuove sfide/penitenze"
WEEKLY_DAY = 6           # giorno di PAUSA + recap + voto: 0=lun ... 6=dom
WEEKLY_HOUR = 20         # ora del recap settimanale
POLL_CLOSE_DAY = 0       # giorno di chiusura voti e assegnazione premi (0=lun)
POLL_CLOSE_HOUR = 10     # ora di chiusura voti

# --- Repertorio: soglie e promemoria ---
MIN_POOL_QUESTS = 4          # sotto questa soglia il bot invita ad aggiungere sfide
MIN_POOL_PENITENZE = 3       # idem per le penitenze
REMIND_ADD_EVERY_DAYS = 4    # ogni quanti giorni ricordare comunque di aggiungerne

# --- Economia / gamification ---
XP_PER_QUEST = 50          # XP base per una sfida completata
COINS_PER_QUEST = 10       # coin per una sfida completata
COINS_PER_ADD = 2          # coin bonus a chi aggiunge una sfida al repertorio
STREAK_BONUS_XP = 10       # XP extra per ogni giorno di streak
STREAK_BONUS_CAP = 100     # tetto massimo del bonus streak
POLL_WINNER_COINS = 30     # premio per chi vince il voto "sfida più bella"
POLL_WINNER_XP = 50
XP_PER_LEVEL = 250         # XP per salire di livello (la gallina cresce)

# --- Negozio: accessori per vestire la gallina ---
# slot = punto dove va indossato (uno alla volta per slot).
# Modifica liberamente prezzi, emoji e oggetti.
SHOP_ITEMS = [
    {"id": "cappello",    "name": "Cappello da cowboy", "emoji": "🤠", "price": 50,  "slot": "testa"},
    {"id": "corona",      "name": "Corona",             "emoji": "👑", "price": 200, "slot": "testa"},
    {"id": "cilindro",    "name": "Cilindro elegante",  "emoji": "🎩", "price": 120, "slot": "testa"},
    {"id": "occhiali",    "name": "Occhiali da sole",   "emoji": "🕶️", "price": 80,  "slot": "occhi"},
    {"id": "fiore",       "name": "Fiore",              "emoji": "🌸", "price": 30,  "slot": "accessorio"},
    {"id": "campanaccio", "name": "Campanaccio",        "emoji": "🔔", "price": 40,  "slot": "accessorio"},
    {"id": "medaglia",    "name": "Medaglia d'oro",     "emoji": "🏅", "price": 150, "slot": "accessorio"},
    {"id": "jetpack",     "name": "Jetpack",            "emoji": "🚀", "price": 300, "slot": "extra"},
    {"id": "arcobaleno",  "name": "Aura arcobaleno",    "emoji": "🌈", "price": 250, "slot": "extra"},
]
# ordine con cui gli accessori indossati appaiono accanto alla gallina
SLOT_ORDER = ["testa", "occhi", "accessorio", "extra"]

# --- Penitenze (votate dal gruppo la domenica) ---
PENITENZA_OPTIONS = 4   # quante penitenze mettere al voto
PENITENZE = [
    "Manda un vocale in cui canti il ritornello di una canzone a caso",
    "Fai 30 flessioni e mandane il video",
    "Posta la foto più imbarazzante che hai in galleria",
    "Racconta al gruppo una figuraccia vera che hai fatto",
    "Fai il verso della gallina (coccodè) camminando per strada, in video",
    "Scrivi un complimento sincero a ogni persona del gruppo",
    "Prepara qualcosa da mangiare e mandane la foto",
    "Manda un vocale imitando qualcuno del gruppo",
]

# --- File di stato (salvato nel repo dalle Actions) ---
STATE_FILE = "data/state.json"

# --- Estetica ---
NICK_PREFIX = "Gallina"   # nickname di default: "Gallina#1", "Gallina#2"...
CELEBRATIONS = [
    "La gallina fa un salto di gioia! 🐔🎉",
    "COCCODÈÈÈ-eraviglioso! 🐔✨",
    "La gallina ti ammira in silenzio. 🐔💖",
    "Un altro traguardo per il pollaio! 🏆",
    "La gallina è fiera di te! 🐔👏",
    "Mangime extra per la gallina stasera! 🌾🐔",
]
