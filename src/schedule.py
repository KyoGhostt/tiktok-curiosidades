"""Agenda de postagem em horário de Brasília. Cada vídeo ocupa o próximo horário livre (continua de onde parou)."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import OUT
import otimo

TZ = ZoneInfo("America/Sao_Paulo")
SLOTS = [(12, 0), (17, 0), (20, 0)]  # picos no Brasil: almoço (12-15h), tarde (16-19h) e noite (20h); evita 23h-3h
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def label(dt):
    return f"{DIAS[dt.weekday()]} {dt:%d/%m} às {dt:%H:%M}"


def quando(dt, ref):
    d = (dt.date() - ref.date()).days
    return f"{'hoje' if d == 0 else 'amanhã' if d == 1 else dt.strftime('%d/%m')} às {dt:%H}h"


def slots_after(t, n):
    """Próximos n horários livres (12h/17h/20h de Brasília) a partir de t, sem estado: usa o que já está agendado."""
    t = t.astimezone(TZ)
    slots = sorted(tuple(x) for x in otimo.load()["slots"])   # horários otimizados (estado/otimizacao.json)
    out, day = [], t.date()
    while len(out) < n:
        if day.weekday() != 6:   # domingo é folga: nenhum vídeo
            for h, m in slots:
                dt = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
                if dt > t and len(out) < n:
                    out.append(dt)
        day += timedelta(days=1)
    return out
