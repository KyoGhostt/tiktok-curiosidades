"""Entrega pelo Telegram (grátis). O token do bot e o chat id vêm de variáveis de ambiente (Secrets)."""
import json, os, requests


def _base():
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    return f"https://api.telegram.org/bot{tok}" if tok else None


def chat_id():
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def configured():
    return bool(_base() and chat_id())


def _call(method, **kw):
    r = requests.post(f"{_base()}/{method}", timeout=300, **kw)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(f"telegram {method}: {j.get('description')}")
    return j["result"]


def send_message(text, silent=False):
    return _call("sendMessage", data={"chat_id": chat_id(), "text": text[:4000], "disable_notification": silent,
                                      "disable_web_page_preview": True})
