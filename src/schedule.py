"""Agenda de postagem em horário de Brasília. Cada vídeo ocupa o próximo horário livre (continua de onde parou)."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import OUT

TZ = ZoneInfo("America/Sao_Paulo")
SLOTS = [(12, 0), (17, 0), (20, 0)]  # picos no Brasil: almoço (12-15h), tarde (16-19h) e noite (20h); evita 23h-3h
STATE = OUT / "schedule_state.json"
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def next_slots(n, now=None):
    now = now or datetime.now(TZ)
    start = now + timedelta(hours=1)
    if STATE.exists():
        last = datetime.fromisoformat(json.loads(STATE.read_text())["last"])
        start = max(start, last + timedelta(minutes=1))
    out, day = [], start.date()
    while len(out) < n:
        for h, m in SLOTS:
            dt = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
            if dt >= start and len(out) < n:
                out.append(dt)
        day += timedelta(days=1)
    STATE.write_text(json.dumps({"last": out[-1].isoformat()}))
    return out


def label(dt):
    return f"{DIAS[dt.weekday()]} {dt:%d/%m} às {dt:%H:%M}"


def quando(dt, ref):
    d = (dt.date() - ref.date()).days
    return f"{'hoje' if d == 0 else 'amanhã' if d == 1 else dt.strftime('%d/%m')} às {dt:%H}h"
