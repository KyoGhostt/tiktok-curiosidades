"""Vigia o Buffer e avisa no Telegram: vídeo postado, erro de postagem e chave de API perto de vencer."""
import os, re, sys
from datetime import datetime, timedelta, timezone, date
import telegram
import buffer_post as bp
import fila

Q = """query($o:OrganizationId!,$s:DateTime!,$e:DateTime!){posts(first:50,input:{organizationId:$o,
  filter:{dueAt:{start:$s,end:$e}},sort:[{field:dueAt,direction:asc}]}){edges{node{id status dueAt sentAt text error{message}}}}}"""


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
    f = fila.load()
    avisados = set(f.get("avisados", []))
    posts = [e["node"] for e in bp.gql(Q, {"o": org, "s": iso(agora - timedelta(hours=40)), "e": iso(agora)})["posts"]["edges"]]
    for p in posts:
        m = re.match(r"^(.*?\(Parte \d+ de \d+\))", p["text"] or "")
        titulo = m.group(1) if m else (p["text"] or p["id"])[:80]
        if p["id"] in avisados:
            continue
        if p["status"] == "sent":
            alert(f"✅ Postado no TikTok: {titulo}"); avisados.add(p["id"])
        elif p["status"] == "error":
            alert(f"❌ Falhou ao postar: {titulo}\n{(p.get('error') or {}).get('message', 'sem detalhe')}"); avisados.add(p["id"])
        elif p["status"] in ("scheduled", "sending") and agora - datetime.fromisoformat(p["dueAt"].replace("Z", "+00:00")) > timedelta(minutes=45):
            alert(f"⏳ Atrasado (status {p['status']}): {titulo}"); avisados.add(p["id"])
    f["avisados"] = sorted(avisados)[-300:]
    fila.save(f)
    criada = os.environ.get("BUFFER_KEY_CREATED", "")
    if criada:
        restam = (date.fromisoformat(criada) + timedelta(days=365) - date.today()).days
        if restam <= 30 and agora.hour == 15:  # avisa 1x por dia
            alert(f"🔑 A chave do Buffer vence em ~{restam} dias. Gere outra em publish.buffer.com/settings/api e troque o secret BUFFER_API_KEY.")


if __name__ == "__main__":
    main()
