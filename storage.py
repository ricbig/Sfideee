"""Gestione dello stato persistente (file JSON, nessun database)."""

import json
import os

from config import STATE_FILE

DEFAULT_STATE = {
    "last_update_id": 0,
    "group_chat_id": None,
    "bot_username": None,       # cache di getMe, per i link privati
    "admin_id": None,           # chi ha fatto /setup diventa admin
    "paused": False,            # pausa vacanze (solo l'admin la cambia)
    "quests": [],
    "next_quest_id": 1,
    "penitenze": [],            # penitenze aggiunte dagli utenti
    "players": {},
    "next_player_seq": 1,       # per i nickname di default "Gallina#N"
    "pending": {},              # uid -> {"action": ...} per input privato
    "current": None,
    "week_assignments": [],
    "week_completions": [],
    "active_polls": [],
    "history": {
        "last_daily_date": None,
        "last_reminder_date": None,
        "last_add_reminder_date": None,
        "last_weekly_date": None,
        "last_poll_close_date": None,
    },
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return json.loads(json.dumps(DEFAULT_STATE))
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, v)
    for k, v in DEFAULT_STATE["history"].items():
        state["history"].setdefault(k, v)
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
