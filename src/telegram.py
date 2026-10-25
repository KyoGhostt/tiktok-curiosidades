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


def send_video(path, caption, duration=0, silent=False):
    """Envia o arquivo e devolve o file_id (para reenviar depois sem novo upload)."""
    with open(path, "rb") as f:
        res = _call("sendVideo", data={"chat_id": chat_id(), "caption": caption[:1024], "supports_streaming": "true",
                                       "width": 1080, "height": 1920, "duration": int(duration),
                                       "disable_notification": silent}, files={"video": f})
    return res["video"]["file_id"]


def resend_video(file_id, caption):
    return _call("sendVideo", data={"chat_id": chat_id(), "video": file_id, "caption": caption[:1024]})
