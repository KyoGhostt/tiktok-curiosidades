"""Testa cada provedor de LLM com um pedido minimo e imprime o resultado (::notice::)."""
import requests, writer
for name, url, key, model in writer.providers():
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=60,
                          json={"model": model, "max_tokens": 20, "messages": [{"role": "user", "content": "diga ok"}]})
        print(f"::notice::{name} {model}: HTTP {r.status_code} {r.text[:140].replace(chr(10), ' ')}", flush=True)
    except Exception as e:
        print(f"::notice::{name}: EXC {str(e)[:120]}", flush=True)
