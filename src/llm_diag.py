"""Testa cada provedor de LLM com um pedido minimo e imprime o resultado (::notice::)."""
import requests, writer
for name, url, key, model in writer.providers():
    try:
        j = writer._chat(url, key, model, "Responda so JSON.", 'Devolva {"ok": 1, "texto": "uma frase de 30 palavras sobre o mar"}', tokens=300)
        print(f"::notice::{name} _chat OK {str(j)[:80]}", flush=True); continue
    except Exception as e:
        print(f"::notice::{name} _chat FALHOU {type(e).__name__} {str(e)[:100]}", flush=True)
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=60,
                          json={"model": model, "max_tokens": 20, "messages": [{"role": "user", "content": "diga ok"}]})
        print(f"::notice::{name} {model}: HTTP {r.status_code} {r.text[:140].replace(chr(10), ' ')}", flush=True)
    except Exception as e:
        print(f"::notice::{name}: EXC {str(e)[:120]}", flush=True)
