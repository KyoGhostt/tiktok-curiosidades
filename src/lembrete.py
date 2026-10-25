"""Roda nos horários de postagem: reenvia o vídeo da parte que deve ser postada agora, com a legenda."""
import json, sys
from datetime import datetime, timedelta, timezone
import telegram


def main(path="info.json"):
    if not telegram.configured():
        print("Telegram não configurado"); return
    info = json.load(open(path))
    now = datetime.now(timezone.utc)
    sent = 0
    for p in info.get("partes", []):
        t = datetime.fromisoformat(p["postar_em"])
        if t - timedelta(minutes=20) <= now <= t + timedelta(minutes=90) and p.get("file_id"):
            telegram.resend_video(p["file_id"], f"⏰ HORA DE POSTAR: Parte {p['parte']}/3 ({p['quando']})\n\n{p['legenda']}")
            sent += 1
    print(f"lembretes enviados: {sent}")


if __name__ == "__main__":
    main(*sys.argv[1:])
