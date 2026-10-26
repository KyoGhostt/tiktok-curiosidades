"""Vigia o Buffer e avisa no Telegram: vídeo postado, erro de postagem, fila vazia e chave de API perto de vencer."""
import os, sys
from datetime import datetime, timedelta, timezone, date
import telegram
import buffer_post as bp

Q = """query($o:OrganizationId!,$s:DateTime!,$e:DateTime!){posts(first:30,input:{organizationId:$o,
  filter:{dueAt:{start:$s,end:$e}},sort:[{field:dueAt,direction:asc}]}){edges{node{id status dueAt sentAt text error{message}}}}}"""
QF = """query($o:OrganizationId!,$s:DateTime!){posts(first:30,input:{organizationId:$o,
  filter:{status:[scheduled],dueAt:{start:$s}}}){edges{node{id}}}}"""
WINDOW_H = float(os.environ.get("WINDOW_H", "3.2"))   # janela igual ao intervalo do cron


def alert(msg):
    print(msg)
    if telegram.configured():
        telegram.send_message(msg)


def main():
    if not bp.key():
        print("sem BUFFER_API_KEY"); return
    agora = datetime.now(timezone.utc)
    try:
        org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
    except Exception as e:
        alert(f"⚠️ A chave de API do Buffer parou de funcionar (venceu ou foi revogada). Gere outra em publish.buffer.com/settings/api e troque o secret BUFFER_API_KEY.\n{str(e)[:200]}")
        sys.exit(1)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    posts = [e["node"] for e in bp.gql(Q, {"o": org, "s": iso(agora - timedelta(hours=WINDOW_H)), "e": iso(agora)})["posts"]["edges"]]
    for p in posts:
        titulo = p["text"].split(" Parte ")[0][:80] if p["text"] else p["id"]
        if p["status"] == "sent":
            alert(f"✅ Postado no TikTok: {titulo}")
        elif p["status"] == "error":
            alert(f"❌ Falhou ao postar: {titulo}\n{(p.get('error') or {}).get('message', 'sem detalhe')}")
        elif p["status"] in ("scheduled", "sending"):
            alert(f"⏳ Ainda não saiu (status {p['status']}): {titulo}")
    fila = bp.gql(QF, {"o": org, "s": iso(agora)})["posts"]["edges"]
    if len(fila) < 3:
        alert(f"📭 Fila do Buffer quase vazia ({len(fila)} agendados). Veja se o gerador diário está rodando.")
    criada = os.environ.get("BUFFER_KEY_CREATED", "")
    if criada:
        restam = (date.fromisoformat(criada) + timedelta(days=365) - date.today()).days
        if restam <= 30 and agora.hour == 15:  # avisa 1x por dia
            alert(f"🔑 A chave do Buffer vence em ~{restam} dias. Gere outra em publish.buffer.com/settings/api e troque o secret BUFFER_API_KEY.")


if __name__ == "__main__":
    main()
