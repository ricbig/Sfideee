"""Wrapper minimale sulle API di Telegram (Bot API via HTTP).

Il bot gira "a tick" (GitHub Actions), quindi leggiamo i messaggi con
getUpdates e rispondiamo, poi il processo termina.
"""

import os

import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BASE = f"https://api.telegram.org/bot{TOKEN}"


def _call(method, **params):
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN non impostato. Aggiungilo nei Secrets del repo "
            "(Settings > Secrets and variables > Actions)."
        )
    params = {k: v for k, v in params.items() if v is not None}
    try:
        r = requests.post(f"{BASE}/{method}", json=params, timeout=30)
        data = r.json()
    except Exception as e:
        print(f"[telegram] eccezione su {method}: {e}")
        return {"ok": False}
    if not data.get("ok"):
        print(f"[telegram] errore su {method}: {data}")
    return data


def _kb(buttons):
    """Costruisce una inline keyboard.

    buttons = lista di righe; ogni riga è una lista di tuple:
      (testo, callback_data)            -> bottone che invia un callback
      (testo, url, "url")               -> bottone che apre un link
    """
    if not buttons:
        return None
    kb = []
    for row in buttons:
        r = []
        for b in row:
            if len(b) > 2 and b[2] == "url":
                r.append({"text": b[0], "url": b[1]})
            else:
                r.append({"text": b[0], "callback_data": b[1]})
        kb.append(r)
    return {"inline_keyboard": kb}


def get_me():
    return _call("getMe")


def get_updates(offset=None):
    return _call(
        "getUpdates",
        offset=offset,
        timeout=0,
        allowed_updates=["message", "callback_query"],
    )


def send_message(chat_id, text, reply_to=None, buttons=None):
    return _call(
        "sendMessage",
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_to_message_id=reply_to,
        reply_markup=_kb(buttons),
        disable_web_page_preview=True,
    )


def edit_message(chat_id, message_id, text, buttons=None):
    return _call(
        "editMessageText",
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        parse_mode="HTML",
        reply_markup=_kb(buttons),
        disable_web_page_preview=True,
    )


def answer_callback(callback_id, text=None, alert=False):
    return _call("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=alert)


def send_poll(chat_id, question, options):
    return _call("sendPoll", chat_id=chat_id, question=question, options=options, is_anonymous=False)


def stop_poll(chat_id, message_id):
    return _call("stopPoll", chat_id=chat_id, message_id=message_id)


def delete_message(chat_id, message_id):
    return _call("deleteMessage", chat_id=chat_id, message_id=message_id)


def send_dice(chat_id, emoji="🎲"):
    return _call("sendDice", chat_id=chat_id, emoji=emoji)
