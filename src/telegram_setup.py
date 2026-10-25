"""Descobre o chat id de quem apertou Start no bot e responde com ele (privado, no próprio Telegram)."""
import os, sys, requests

tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not tok:
    print("::error title=Telegram::FALTA o secret TELEGRAM_BOT_TOKEN (nao encontrado ou vazio)"); sys.exit(1)
base = f"https://api.telegram.org/bot{tok}"
me = requests.get(f"{base}/getMe", timeout=30).json()
if not me.get("ok"):
    print("::error title=Telegram::TOKEN INVALIDO: " + str(me.get("description"))); sys.exit(1)
ups = requests.get(f"{base}/getUpdates", timeout=30).json().get("result", [])
msgs = [u["message"] for u in ups if "message" in u]
if not msgs:
    print(f"::error title=Telegram::NENHUMA MENSAGEM para o bot @{me['result']['username']}. Abra esse bot no Telegram, aperte Start, mande oi e rode de novo."); sys.exit(1)
cid = msgs[-1]["chat"]["id"]
requests.post(f"{base}/sendMessage", timeout=30, data={"chat_id": cid, "text":
    f"✅ Conectado!\n\nSeu chat id é: {cid}\n\nGuarde esse número no GitHub, em Settings > Secrets and variables > Actions, "
    f"com o nome TELEGRAM_CHAT_ID. Depois é só me avisar."})
print("OK: mensagem enviada ao usuário (o chat id foi enviado só no Telegram, não aparece aqui)")
