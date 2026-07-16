"""Questr Bot — sfide giornaliere gamificate per un gruppo di amici.

Gira "a tick" su GitHub Actions. Architettura:
  • NEL GRUPPO (a bottoni): pannello, profilo/gallina, negozio e acquisti,
    classifica, nickname, sfida del giorno, consegne, recap, voti.
  • IN PRIVATO col bot: SOLO aggiunta di sfide e penitenze (restano segrete
    e vengono estratte a sorteggio → sorpresa per tutti). Qui l'admin può
    anche mettere in pausa il gioco (vacanze).
"""

import random
from datetime import date, datetime, timedelta

import config
import telegram_api as tg
from storage import load_state, save_state


# ======================================================================
# Tempo
# ======================================================================
def now_local():
    return datetime.now(config.TIMEZONE)


def today_str():
    return now_local().date().isoformat()


def is_rest_day():
    return now_local().weekday() == config.WEEKLY_DAY


# ======================================================================
# Giocatori, livelli, estetica
# ======================================================================
def get_player(state, user):
    """Ottiene/crea il giocatore. Nessun nome vero: nickname di default
    'Gallina#N' modificabile. I nuovi entrano nella rotazione senza raffiche
    (partono dal conteggio più alto attuale)."""
    uid = str(user["id"])
    if uid not in state["players"]:
        seq = state.get("next_player_seq", 1)
        state["next_player_seq"] = seq + 1
        maxc = max((pp.get("assigned_count", 0) for pp in state["players"].values()), default=0)
        state["players"][uid] = {
            "name": f"{config.NICK_PREFIX}#{seq}",
            "xp": 0, "coins": 0, "streak": 0, "best_streak": 0,
            "completed": 0, "playing": True,
            "last_completed_date": None, "last_assigned_date": None,
            "assigned_count": maxc,          # per la rotazione equa
            "inventory": [], "equipped": {},
        }
    else:
        p = state["players"][uid]
        p.setdefault("inventory", [])
        p.setdefault("equipped", {})
        p.setdefault("assigned_count", 0)
    return state["players"][uid]


def level_from_xp(xp):
    return xp // config.XP_PER_LEVEL + 1


def cow_stage(level):
    if level < 3:
        return "pulcino"
    if level < 6:
        return "gallina giovane"
    if level < 10:
        return "gallina in forma"
    if level < 15:
        return "super gallina"
    return "gallina leggendaria"


def find_item(key):
    if not key:
        return None
    key = key.strip().lower()
    for it in config.SHOP_ITEMS:
        if it["id"] == key:
            return it
    for it in config.SHOP_ITEMS:
        if key in it["name"].lower():
            return it
    return None


def cow_line(player):
    lvl = level_from_xp(player["xp"])
    deco = ""
    for slot in config.SLOT_ORDER:
        iid = player.get("equipped", {}).get(slot)
        it = find_item(iid) if iid else None
        if it:
            deco += it["emoji"]
    return f"🐔{deco} · {cow_stage(lvl)} · Lv {lvl}"


def xp_bar(xp):
    lvl = level_from_xp(xp)
    into = xp - (lvl - 1) * config.XP_PER_LEVEL
    filled = max(0, min(10, int(round(into / config.XP_PER_LEVEL * 10))))
    return "🟩" * filled + "⬜" * (10 - filled) + f"  {into}/{config.XP_PER_LEVEL} XP"


def pen_pool(state):
    return list(config.PENITENZE) + list(state.get("penitenze", []))


def bot_username(state):
    if not state.get("bot_username"):
        res = tg.get_me()
        if res.get("ok"):
            state["bot_username"] = res["result"].get("username")
    return state.get("bot_username")


def deep_link(state, param):
    u = bot_username(state)
    return f"https://t.me/{u}?start={param}" if u else "https://t.me"


def is_admin(state, uid):
    return state.get("admin_id") == uid


# ======================================================================
# Schermate del GRUPPO (tutte a bottoni)
# ======================================================================
def group_panel(state):
    status = "  ⏸️ <i>in pausa</i>" if state.get("paused") else ""
    text = (
        f"🎛️ <b>Pannello Questr</b>{status}\n"
        f"📋 {len(state['quests'])} sfide · 😈 {len(pen_pool(state))} penitenze nel repertorio\n"
        "Gestisci tutto dai bottoni 👇"
    )
    buttons = [
        [("🐔 La mia gallina", "open_profile"), ("🏪 Negozio", "open_shop")],
        [("🏆 Classifica", "lb"), ("✏️ Nickname", deep_link(state, "nick"), "url")],
        [("➕ Aggiungi sfida", deep_link(state, "addquest"), "url"),
         ("😈 Aggiungi penitenza", deep_link(state, "addpen"), "url")],
        [("ℹ️ Come funziona", "help")],
    ]
    return text, buttons


def render_profile(player, uid):
    inv = player.get("inventory", [])
    owned = " ".join(find_item(i)["emoji"] for i in inv if find_item(i)) or "—"
    text = (
        f"🐔 <b>{player['name']}</b>\n\n"
        f"{cow_line(player)}\n{xp_bar(player['xp'])}\n\n"
        f"🪙 Coin: <b>{player['coins']}</b>\n"
        f"🔥 Streak: <b>{player['streak']}</b> (record {player.get('best_streak', 0)})\n"
        f"✅ Sfide completate: <b>{player['completed']}</b>\n"
        f"🎒 Accessori: {owned}"
    )
    buttons = [[("🏪 Negozio", f"shop:{uid}")], [("✖️ Chiudi", f"close:{uid}")]]
    return text, buttons


def render_shop(player, uid):
    inv = player.get("inventory", [])
    eq = set(player.get("equipped", {}).values())
    text = (
        f"🏪 <b>Negozio di {player['name']}</b> — {player['coins']} 🪙\n\n"
        f"{cow_line(player)}\n\nTocca per comprare o (dis)indossare:"
    )
    buttons = []
    for it in config.SHOP_ITEMS:
        if it["id"] in inv:
            mark = "✅" if it["id"] in eq else "👕"
            buttons.append([(f"{mark} {it['emoji']} {it['name']} (tuo)", f"equip:{it['id']}:{uid}")])
        else:
            lock = "🟢" if player["coins"] >= it["price"] else "🔒"
            buttons.append([(f"{lock} {it['emoji']} {it['name']} — {it['price']}🪙", f"buy:{it['id']}:{uid}")])
    buttons.append([("🐔 Profilo", f"profile:{uid}"), ("✖️ Chiudi", f"close:{uid}")])
    return text, buttons


def leaderboard_text(state):
    players = list(state["players"].items())
    if not players:
        return "Ancora nessun giocatore. Usate /entra!"
    players.sort(key=lambda x: (x[1]["xp"], x[1]["coins"]), reverse=True)
    lines = ["🏆 <b>Classifica</b>", ""]
    medals = ["🥇", "🥈", "🥉"]
    for i, (_, p) in enumerate(players[:10]):
        pre = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{pre} <b>{p['name']}</b> — Lv {level_from_xp(p['xp'])} · {p['xp']}XP · {p['coins']}🪙 · {p['streak']}🔥")
    return "\n".join(lines)


def help_text():
    return (
        "ℹ️ <b>Come funziona</b>\n\n"
        f"Ogni giorno (tranne domenica) alle {config.DAILY_HOUR:02d}:00 una sfida tocca a "
        "una persona <b>a rotazione equa</b>: tutti fanno lo stesso numero di turni.\n"
        "Fai la sfida → manda <b>foto/video</b> nel gruppo → tocca <b>✅ valida</b>.\n\n"
        "🏅 XP e coin, livelli della gallina, streak 🔥\n"
        f"⏰ Alle {config.REMINDER_HOUR:02d}:00 un promemoria privato se non hai consegnato.\n"
        "🏪 Coin → accessori per la gallina (qui nel gruppo).\n"
        "🤫 <b>Sfide e penitenze si aggiungono in privato col bot</b>: restano segrete "
        "e vengono estratte a sorteggio.\n"
        "😴 <b>Domenica</b>: riposo, recap, voto sulla sfida più bella e penitenza per chi ha saltato."
    )


# ======================================================================
# Completamento sfida
# ======================================================================
def do_complete(state, player, uid, proof_message_id):
    cur = state["current"]
    cur["completed"] = True
    cur["proof_message_id"] = proof_message_id

    today = now_local().date()
    last = player.get("last_completed_date")
    if last:
        last_d = date.fromisoformat(last)
        if last_d == today - timedelta(days=1):
            player["streak"] += 1
        elif last_d == today:
            pass
        else:
            player["streak"] = 1
    else:
        player["streak"] = 1
    player["best_streak"] = max(player.get("best_streak", 0), player["streak"])
    player["last_completed_date"] = today.isoformat()

    bonus = min(config.STREAK_BONUS_XP * player["streak"], config.STREAK_BONUS_CAP)
    gained = config.XP_PER_QUEST + bonus
    player["xp"] += gained
    player["coins"] += config.COINS_PER_QUEST
    player["completed"] += 1

    state["week_completions"].append(
        {"date": today.isoformat(), "quest_text": cur["quest_text"],
         "player_id": uid, "player_name": player["name"]}
    )
    for a in state["week_assignments"]:
        if a["date"] == cur["date"] and a["assigned_to_id"] == uid:
            a["completed"] = True
    return gained


def celebrate(state, chat_id, player, gained):
    tg.send_dice(chat_id, "🎯")
    tg.send_message(
        chat_id,
        f"{random.choice(config.CELEBRATIONS)}\n\n"
        f"🎉 <b>{player['name']}</b> ha completato la sfida!\n"
        f"➕ {gained} XP (streak {player['streak']}🔥) · +{config.COINS_PER_QUEST} 🪙\n"
        f"{cow_line(player)}\n{xp_bar(player['xp'])}",
        buttons=[[("🏪 Negozio", "open_shop"), ("🏆 Classifica", "lb")]],
    )


# ======================================================================
# Messaggi in arrivo
# ======================================================================
def handle_update(state, update):
    state["last_update_id"] = update["update_id"]
    if "callback_query" in update:
        handle_callback(state, update["callback_query"])
    elif "message" in update:
        handle_message(state, update["message"])


def handle_message(state, msg):
    chat = msg["chat"]
    chat_id = chat["id"]
    ctype = chat.get("type")
    user = msg.get("from")
    if not user or user.get("is_bot"):
        return
    uid = str(user["id"])
    text = msg.get("text", "") or ""
    is_private = ctype == "private"
    has_media = any(k in msg for k in ("photo", "video", "animation", "document"))

    # foto/video nel gruppo da chi ha la sfida -> proponi validazione
    if not is_private and has_media:
        cur = state.get("current")
        if cur and not cur.get("completed") and cur["assigned_to_id"] == uid:
            tg.send_message(chat_id, "📸 È la consegna della sfida di oggi?",
                            reply_to=msg["message_id"],
                            buttons=[[("✅ Sì, valida!", f"validate:{msg['message_id']}")]])
        return

    if text.startswith("/"):
        handle_command(state, msg, chat_id, ctype, is_private, user, uid, text)
        return

    # testo libero in privato -> completa un'azione in sospeso (sfida/penitenza/nickname)
    if is_private:
        pend = state.get("pending", {}).get(uid)
        if pend:
            consume_pending(state, chat_id, user, uid, pend, text)
            state["pending"].pop(uid, None)


def handle_command(state, msg, chat_id, ctype, is_private, user, uid, text):
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    player = get_player(state, user)

    if cmd == "/start":
        if is_private:
            if arg == "addquest":
                start_pending(state, chat_id, uid, "add_quest")
            elif arg == "addpen":
                start_pending(state, chat_id, uid, "add_pen")
            elif arg == "nick":
                start_pending(state, chat_id, uid, "add_nick")
            else:
                t, b = private_menu(state, uid)
                tg.send_message(chat_id, t, buttons=b)
        else:
            t, b = group_panel(state)
            tg.send_message(chat_id, t, buttons=b)

    elif cmd in ("/menu", "/pannello"):
        if is_private:
            t, b = private_menu(state, uid)
        else:
            t, b = group_panel(state)
        tg.send_message(chat_id, t, buttons=b)

    elif cmd in ("/help", "/aiuto"):
        tg.send_message(chat_id, help_text())

    elif cmd == "/setup":
        if ctype in ("group", "supergroup"):
            state["group_chat_id"] = chat_id
            if not state.get("admin_id"):
                state["admin_id"] = uid   # chi fa /setup diventa admin
            tg.send_message(chat_id, "✅ Gruppo registrato! Ecco il pannello 👇")
            t, b = group_panel(state)
            tg.send_message(chat_id, t, buttons=b)
        else:
            tg.send_message(chat_id, "Usa /setup <b>dentro il gruppo</b>.")

    elif cmd == "/entra":
        player["playing"] = True
        # riallinea alla rotazione per non creare raffiche
        active_counts = [p.get("assigned_count", 0) for u, p in state["players"].items()
                         if p.get("playing") and u != uid]
        if active_counts:
            player["assigned_count"] = max(player.get("assigned_count", 0), max(active_counts))
        extra, btns = "", None
        if player["name"].startswith(config.NICK_PREFIX + "#"):
            extra = f"\n\nVuoi un nickname invece di {player['name']}?"
            btns = [[("✏️ Scegli nickname", deep_link(state, "nick"), "url")]]
        tg.send_message(chat_id, f"🐔 {player['name']} è nel gioco!{extra}", buttons=btns)

    elif cmd == "/esci":
        player["playing"] = False
        tg.send_message(chat_id, f"{player['name']} non riceverà più sfide (resta in classifica).")

    elif cmd in ("/nickname", "/nick"):
        if arg:
            set_nick(state, chat_id, player, arg)
        else:
            if is_private:
                start_pending(state, chat_id, uid, "add_nick")
            else:
                tg.send_message(chat_id, "Scrivi il nome dopo il comando, es: <code>/nickname Ricky</code>")

    elif cmd == "/aggiungi":
        if is_private:
            add_quest(state, chat_id, player, arg) if arg else start_pending(state, chat_id, uid, "add_quest")
        else:
            tg.send_message(chat_id, "🤫 Le sfide si aggiungono in privato col bot (così restano segrete)!",
                            buttons=[[("➕ Aggiungi in privato", deep_link(state, "addquest"), "url")]])

    elif cmd == "/aggiungipenitenza":
        if is_private:
            add_pen(state, chat_id, arg) if arg else start_pending(state, chat_id, uid, "add_pen")
        else:
            tg.send_message(chat_id, "🤫 Le penitenze si aggiungono in privato col bot!",
                            buttons=[[("😈 Aggiungi in privato", deep_link(state, "addpen"), "url")]])

    elif cmd == "/sfide":
        tg.send_message(chat_id, f"📋 {len(state['quests'])} sfide · 😈 {len(pen_pool(state))} penitenze nel repertorio.")

    elif cmd == "/fatto":
        do_fatto_command(state, chat_id, msg, uid, player)

    elif cmd in ("/gallina", "/profilo"):
        t, b = render_profile(player, uid)
        tg.send_message(chat_id, t, buttons=b)

    elif cmd == "/negozio":
        t, b = render_shop(player, uid)
        tg.send_message(chat_id, t, buttons=b)

    elif cmd == "/classifica":
        tg.send_message(chat_id, leaderboard_text(state))

    # --- comandi admin (solo in privato) ---
    elif cmd == "/pausa":
        admin_set_pause(state, chat_id, uid, True)
    elif cmd in ("/riprendi", "/riparti"):
        admin_set_pause(state, chat_id, uid, False)

    else:
        tg.send_message(chat_id, "Comando non riconosciuto. Prova /menu")


def do_fatto_command(state, chat_id, msg, uid, player):
    cur = state.get("current")
    if not cur or cur.get("completed"):
        tg.send_message(chat_id, "Non c'è una sfida attiva da completare adesso.")
        return
    if cur["assigned_to_id"] != uid:
        tg.send_message(chat_id, f"La sfida di oggi è di {cur['assigned_to_name']}, non tua 😄")
        return
    reply = msg.get("reply_to_message")
    ok = reply and any(k in reply for k in ("photo", "video", "animation", "document"))
    if not ok:
        tg.send_message(chat_id, "📸 Rispondi alla tua <b>foto o video</b> con /fatto (o usa il bottone ✅).")
        return
    gained = do_complete(state, player, uid, reply["message_id"])
    celebrate(state, chat_id, player, gained)


# ======================================================================
# Menu privato (solo aggiunte + admin)
# ======================================================================
def private_menu(state, uid):
    text = (
        "🤫 <b>Aggiunte segrete</b>\n\n"
        "Qui aggiungi sfide e penitenze: nessuno le vede, escono a sorteggio.\n"
        f"📋 {len(state['quests'])} sfide · 😈 {len(pen_pool(state))} penitenze nel repertorio."
    )
    buttons = [
        [("➕ Aggiungi sfida", "addq"), ("😈 Aggiungi penitenza", "addp")],
    ]
    if is_admin(state, uid):
        if state.get("paused"):
            buttons.append([("▶️ Riprendi il gioco", "resume")])
        else:
            buttons.append([("⏸️ Pausa (vacanze)", "pause")])
    return text, buttons


def start_pending(state, chat_id, uid, action):
    state.setdefault("pending", {})[uid] = {"action": action}
    prompts = {
        "add_quest": "➕ <b>Nuova sfida</b>\nScrivimi il testo. Resterà segreta! 🤫",
        "add_pen": "😈 <b>Nuova penitenza</b>\nScrivimi il testo.",
        "add_nick": "✏️ <b>Nickname</b>\nScrivimi come vuoi farti chiamare.",
    }
    tg.send_message(chat_id, prompts[action], buttons=[[("❌ Annulla", "cancel")]])


def consume_pending(state, chat_id, user, uid, pend, text):
    player = get_player(state, user)
    text = text.strip()
    if not text:
        tg.send_message(chat_id, "Testo vuoto, riprova dal /menu.")
        return
    a = pend["action"]
    if a == "add_quest":
        add_quest(state, chat_id, player, text)
    elif a == "add_pen":
        add_pen(state, chat_id, text)
    elif a == "add_nick":
        set_nick(state, chat_id, player, text)


def add_quest(state, chat_id, player, text):
    state["quests"].append({"id": state["next_quest_id"], "text": text, "author_name": player["name"]})
    state["next_quest_id"] += 1
    player["coins"] += config.COINS_PER_ADD
    tg.send_message(chat_id, f"✅ Sfida segreta salvata! (totale {len(state['quests'])}) +{config.COINS_PER_ADD}🪙",
                    buttons=[[("➕ Un'altra", "addq"), ("😈 Penitenza", "addp")]])


def add_pen(state, chat_id, text):
    state.setdefault("penitenze", []).append(text)
    tg.send_message(chat_id, f"😈 Penitenza salvata! (totale {len(pen_pool(state))})",
                    buttons=[[("😈 Un'altra", "addp"), ("➕ Sfida", "addq")]])


def set_nick(state, chat_id, player, text):
    player["name"] = text[:24]
    tg.send_message(chat_id, f"✏️ Ok! D'ora in poi sei <b>{player['name']}</b> 🐔")


def admin_set_pause(state, chat_id, uid, value):
    if not is_admin(state, uid):
        tg.send_message(chat_id, "🔒 Solo l'admin (chi ha fatto /setup) può farlo.")
        return
    state["paused"] = value
    group = state.get("group_chat_id")
    if value:
        tg.send_message(chat_id, "⏸️ Gioco in pausa. Niente sfide né promemoria finché non riprendi.")
        if group:
            tg.send_message(group, "⏸️ <b>Questr in pausa</b> (modalità vacanza). Ci si rivede presto! 🏖️🐔")
    else:
        tg.send_message(chat_id, "▶️ Gioco ripreso!")
        if group:
            tg.send_message(group, "▶️ <b>Questr riparte!</b> Le sfide tornano da oggi. 🐔")


# ======================================================================
# Callback dei bottoni
# ======================================================================
def handle_callback(state, cb):
    data = cb.get("data", "")
    user = cb["from"]
    uid = str(user["id"])
    msg = cb.get("message") or {}
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    message_id = msg.get("message_id")
    is_private = chat.get("type") == "private"
    player = get_player(state, user)

    def ans(text=None, alert=False):
        tg.answer_callback(cb["id"], text, alert)

    # segmenti tipo "buy:cappello:12345" -> owner nell'ultimo pezzo
    seg = data.split(":")
    head = seg[0]
    owner = seg[-1] if len(seg) >= 2 and seg[-1].isdigit() else None

    # protezione: i pannelli personali sono di chi li ha aperti
    if owner and owner != uid:
        ans("Questo è di un'altra persona — apri il tuo dal pannello 🐔", alert=True)
        return

    # apertura pannelli personali (creano un messaggio nuovo per chi preme)
    if head == "open_profile":
        ans()
        t, b = render_profile(player, uid)
        tg.send_message(chat_id, t, buttons=b)
    elif head == "open_shop":
        ans()
        t, b = render_shop(player, uid)
        tg.send_message(chat_id, t, buttons=b)
    elif head == "lb":
        ans()
        tg.send_message(chat_id, leaderboard_text(state))
    elif head == "help":
        ans()
        tg.send_message(chat_id, help_text())

    # navigazione dentro i pannelli personali (modifica il messaggio)
    elif head == "profile":
        ans()
        t, b = render_profile(player, uid)
        tg.edit_message(chat_id, message_id, t, buttons=b)
    elif head == "shop":
        ans()
        t, b = render_shop(player, uid)
        tg.edit_message(chat_id, message_id, t, buttons=b)
    elif head == "close":
        ans()
        tg.delete_message(chat_id, message_id)

    # negozio: comprare / (dis)indossare
    elif head == "buy":
        it = find_item(seg[1])
        if not it:
            ans("Oggetto non trovato", alert=True)
        elif it["id"] in player.get("inventory", []):
            ans("Ce l'hai già!")
        elif player["coins"] < it["price"]:
            ans(f"Ti mancano {it['price'] - player['coins']} 🪙", alert=True)
        else:
            player["coins"] -= it["price"]
            player.setdefault("inventory", []).append(it["id"])
            player.setdefault("equipped", {})[it["slot"]] = it["id"]
            ans(f"Comprato {it['emoji']} {it['name']}!")
            t, b = render_shop(player, uid)
            tg.edit_message(chat_id, message_id, t, buttons=b)
    elif head == "equip":
        it = find_item(seg[1])
        if it and it["id"] in player.get("inventory", []):
            eq = player.setdefault("equipped", {})
            if eq.get(it["slot"]) == it["id"]:
                del eq[it["slot"]]
                ans(f"Tolto {it['emoji']}")
            else:
                eq[it["slot"]] = it["id"]
                ans(f"Indossato {it['emoji']}")
            t, b = render_shop(player, uid)
            tg.edit_message(chat_id, message_id, t, buttons=b)
        else:
            ans("Non lo possiedi", alert=True)

    # aggiunte private
    elif head == "addq":
        ans(); start_pending(state, chat_id, uid, "add_quest")
    elif head == "addp":
        ans(); start_pending(state, chat_id, uid, "add_pen")
    elif head == "nick":
        ans(); start_pending(state, chat_id, uid, "add_nick")
    elif head == "cancel":
        state.get("pending", {}).pop(uid, None)
        ans("Annullato")
        t, b = private_menu(state, uid)
        if message_id:
            tg.edit_message(chat_id, message_id, t, buttons=b)

    # admin pausa
    elif head == "pause":
        ans(); admin_set_pause(state, chat_id, uid, True)
    elif head == "resume":
        ans(); admin_set_pause(state, chat_id, uid, False)

    # validazione consegna
    elif head == "validate":
        cur = state.get("current")
        if not cur or cur.get("completed"):
            ans("Già validata o nessuna sfida attiva")
        elif cur["assigned_to_id"] != uid:
            ans("Non è la tua sfida 😄", alert=True)
        else:
            gained = do_complete(state, player, uid, int(seg[1]))
            ans("Validata! 🎉")
            celebrate(state, chat_id, player, gained)
    else:
        ans()


# ======================================================================
# Selezione a rotazione equa
# ======================================================================
def pick_assignee(active):
    """active = lista (uid, player) dei giocatori attivi. Sceglie chi ha il
    minor numero di turni; a parità, chi non gioca da più tempo; poi random."""
    active.sort(key=lambda it: (it[1].get("assigned_count", 0),
                                it[1].get("last_assigned_date") or "0000-00-00"))
    min_count = active[0][1].get("assigned_count", 0)
    cands = [it for it in active if it[1].get("assigned_count", 0) == min_count]
    return random.choice(cands)


# ======================================================================
# Azioni programmate
# ======================================================================
def close_pending_assignment(state):
    cur = state.get("current")
    if not cur:
        return
    if not cur.get("completed"):
        p = state["players"].get(cur["assigned_to_id"])
        if p:
            p["streak"] = 0
    state["current"] = None


def maybe_daily(state):
    n = now_local()
    if n.hour < config.DAILY_HOUR:
        return
    if state["history"]["last_daily_date"] == today_str():
        return
    group = state.get("group_chat_id")
    if not group:
        return

    # domenica = riposo
    if is_rest_day():
        state["history"]["last_daily_date"] = today_str()
        tg.send_message(group, "😴 <b>Domenica di riposo!</b> Niente sfida oggi. Stasera recap e voti 🗳️")
        return

    close_pending_assignment(state)

    quests = state["quests"]
    active = [(uid, p) for uid, p in state["players"].items() if p.get("playing")]
    state["history"]["last_daily_date"] = today_str()

    if not active:
        tg.send_message(group, "🐔 Nessun giocatore in rotazione! Scrivete <b>/entra</b> per giocare.")
        return
    if not quests:
        tg.send_message(group, "📋 Repertorio vuoto! Aggiungete qualche sfida per iniziare 👇",
                        buttons=[[("➕ Aggiungi sfida", deep_link(state, "addquest"), "url")]])
        return

    uid, player = pick_assignee(active)
    quest = random.choice(quests)
    today = today_str()
    player["last_assigned_date"] = today
    player["assigned_count"] = player.get("assigned_count", 0) + 1

    state["current"] = {
        "date": today, "quest_id": quest["id"], "quest_text": quest["text"],
        "assigned_to_id": uid, "assigned_to_name": player["name"],
        "completed": False, "proof_message_id": None,
    }
    state["week_assignments"].append(
        {"date": today, "assigned_to_id": uid, "assigned_to_name": player["name"],
         "quest_text": quest["text"], "completed": False}
    )

    tg.send_message(
        group,
        "🐔✨ <b>SFIDA DEL GIORNO</b> ✨🐔\n\n"
        f"👉 Tocca a <b>{player['name']}</b>!\n\n"
        f"🎯 {quest['text']}\n\n"
        "Fai la sfida, manda <b>foto o video</b> qui e tocca <b>✅ valida</b>.\n"
        "⏰ Hai tempo fino a domani mattina!",
    )


def maybe_reminder(state):
    """Promemoria PRIVATO alla sola persona di turno."""
    if is_rest_day():
        return
    n = now_local()
    if n.hour < config.REMINDER_HOUR:
        return
    if state["history"]["last_reminder_date"] == today_str():
        return
    cur = state.get("current")
    if not cur or cur.get("completed") or cur.get("date") != today_str():
        return
    uid = cur["assigned_to_id"]
    res = tg.send_message(
        int(uid),
        "⏰ <b>Psst… ci sei?</b>\n\n"
        f"La tua sfida di oggi è ancora da fare:\n🎯 {cur['quest_text']}\n\n"
        "La gallina ti aspetta! 🐔 Manda foto/video nel gruppo e valida.",
    )
    if not res.get("ok"):
        print(f"[reminder] non riesco a scrivere in privato a {uid} (deve premere Start sul bot)")
    state["history"]["last_reminder_date"] = today_str()


def maybe_add_reminder(state):
    """Ricorda di aggiungere sfide/penitenze: se il repertorio è basso,
    oppure comunque ogni tot giorni. Niente silenzio."""
    n = now_local()
    if n.hour < config.ADD_REMINDER_HOUR:
        return
    if state["history"]["last_add_reminder_date"] == today_str():
        return
    group = state.get("group_chat_id")
    if not group:
        return

    nq = len(state["quests"])
    npn = len(pen_pool(state))
    low_q = nq < config.MIN_POOL_QUESTS
    low_p = npn < config.MIN_POOL_PENITENZE
    last = state["history"]["last_add_reminder_date"]
    regular = last is None or (date.fromisoformat(today_str()) - date.fromisoformat(last)).days >= config.REMIND_ADD_EVERY_DAYS

    if not (low_q or low_p or regular):
        return

    if low_q or low_p:
        parti = []
        if low_q:
            parti.append(f"restano solo <b>{nq}</b> sfide")
        if low_p:
            parti.append(f"solo <b>{npn}</b> penitenze")
        msg = "🍽️ La gallina ha fame di idee: " + " e ".join(parti) + "!\nAggiungetene di nuove 👇"
    else:
        msg = "💡 Promemoria: aggiungete <b>nuove sfide e penitenze</b> per tenere il gioco fresco! 🐔"

    tg.send_message(group, msg, buttons=[
        [("➕ Aggiungi sfida", deep_link(state, "addquest"), "url"),
         ("😈 Aggiungi penitenza", deep_link(state, "addpen"), "url")],
    ])
    state["history"]["last_add_reminder_date"] = today_str()


def maybe_weekly(state):
    n = now_local()
    if n.weekday() != config.WEEKLY_DAY or n.hour < config.WEEKLY_HOUR:
        return
    if state["history"]["last_weekly_date"] == today_str():
        return
    group = state.get("group_chat_id")
    if not group:
        return

    comps = state["week_completions"]
    state["active_polls"] = []

    if comps:
        lines = ["📅 <b>RECAP DELLA SETTIMANA</b> 🐔", ""]
        for c in comps:
            lines.append(f"✅ <b>{c['player_name']}</b>: {c['quest_text']}")
        tg.send_message(group, "\n".join(lines))
    else:
        tg.send_message(group, "📅 Questa settimana nessuna sfida completata... 🐔💤")

    # voto sfida più bella
    if comps:
        uniq, seen = [], set()
        for c in comps:
            if c["player_id"] not in seen:
                seen.add(c["player_id"])
                uniq.append(c)
        uniq = uniq[:10]
        options = [f"{c['player_name']}: {c['quest_text'][:40]}" for c in uniq]
        if len(options) >= 2:
            res = tg.send_poll(group, "🏆 Chi ha fatto la sfida più bella?", options)
            if res.get("ok"):
                state["active_polls"].append({"type": "best", "chat_id": group,
                                              "message_id": res["result"]["message_id"],
                                              "players": [c["player_id"] for c in uniq]})

    # voto penitenza per chi ha saltato
    missed = [a for a in state["week_assignments"] if not a.get("completed")]
    pool = pen_pool(state)
    if missed:
        names = sorted({a["assigned_to_name"] for a in missed})
        if len(pool) >= 2:
            k = min(config.PENITENZA_OPTIONS, len(pool))
            sample = random.sample(pool, k)
            res = tg.send_poll(group, (f"😈 Che penitenza per {', '.join(names)}?")[:290],
                               [p[:90] for p in sample])
            if res.get("ok"):
                state["active_polls"].append({"type": "penitenza", "chat_id": group,
                                              "message_id": res["result"]["message_id"],
                                              "options_text": sample, "missers": names})
        else:
            tg.send_message(group, f"😈 {', '.join(names)} avrebbero una penitenza, ma il repertorio è vuoto!"
                                   " Aggiungetene 👇",
                            buttons=[[("😈 Aggiungi penitenza", deep_link(state, "addpen"), "url")]])

    state["history"]["last_weekly_date"] = today_str()
    state["week_completions"] = []
    state["week_assignments"] = []


def maybe_close_polls(state):
    n = now_local()
    polls = state.get("active_polls") or []
    if not polls:
        return
    if n.weekday() != config.POLL_CLOSE_DAY or n.hour < config.POLL_CLOSE_HOUR:
        return
    if state["history"]["last_poll_close_date"] == today_str():
        return

    for poll in polls:
        res = tg.stop_poll(poll["chat_id"], poll["message_id"])
        if not res.get("ok"):
            continue
        opts = res["result"]["options"]
        idx = max(range(len(opts)), key=lambda i: opts[i]["voter_count"])
        votes = opts[idx]["voter_count"]

        if poll["type"] == "best":
            if votes > 0:
                wp = state["players"].get(poll["players"][idx])
                if wp:
                    wp["coins"] += config.POLL_WINNER_COINS
                    wp["xp"] += config.POLL_WINNER_XP
                    tg.send_message(poll["chat_id"],
                                    f"🏆👑 Sfida della settimana a <b>{wp['name']}</b> ({votes} voti)!\n"
                                    f"+{config.POLL_WINNER_COINS}🪙 +{config.POLL_WINNER_XP} XP")
            else:
                tg.send_message(poll["chat_id"], "Nessun voto sulla sfida più bella 🤷")
        elif poll["type"] == "penitenza":
            names = ", ".join(poll.get("missers", []))
            if votes > 0:
                tg.send_message(poll["chat_id"],
                                f"😈🔨 <b>Penitenza decisa dal gruppo</b> ({votes} voti)!\n"
                                f"Tocca a: <b>{names}</b>\n👉 {poll['options_text'][idx]}\n"
                                "Da fare entro stasera!")
            else:
                tg.send_message(poll["chat_id"], f"Nessun voto sulla penitenza: {names} se la cavano 😅")

    state["active_polls"] = []
    state["history"]["last_poll_close_date"] = today_str()


# ======================================================================
# Tick
# ======================================================================
def main():
    state = load_state()
    bot_username(state)

    offset = state["last_update_id"] + 1 if state["last_update_id"] else None
    resp = tg.get_updates(offset=offset)
    if resp.get("ok"):
        for update in resp["result"]:
            try:
                handle_update(state, update)
            except Exception as e:
                print(f"[errore update] {e}")

    # le azioni automatiche si fermano in pausa (vacanze); i voti aperti si chiudono comunque
    if not state.get("paused"):
        for action in (maybe_daily, maybe_reminder, maybe_add_reminder, maybe_weekly):
            try:
                action(state)
            except Exception as e:
                print(f"[errore {action.__name__}] {e}")
    try:
        maybe_close_polls(state)
    except Exception as e:
        print(f"[errore maybe_close_polls] {e}")

    save_state(state)


if __name__ == "__main__":
    main()
