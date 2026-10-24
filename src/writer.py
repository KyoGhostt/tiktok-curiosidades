"""Roteirista: LLM free via Hugging Face Inference Providers."""
import json, re, requests
from config import HF_TOKEN, LLM_MODEL

SYSTEM = """Você escreve roteiros curtos de curiosidades para TikTok em português do Brasil.
Regras: gancho forte na primeira frase (máx 12 palavras), 90 a 130 palavras no total,
frases curtas, tom empolgado mas natural, use SOMENTE fatos presentes no texto-base fornecido,
nunca invente números ou datas, termine com uma pergunta que gere comentários.
Responda APENAS em JSON válido: {"titulo": str, "roteiro": str, "palavras_chave_busca": [3 termos em inglês para buscar vídeos de fundo], "hashtags": [5 hashtags sem #]}"""


def write_script(topic, base_text):
    r = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"model": LLM_MODEL, "temperature": 0.8, "max_tokens": 700,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": f"Tema: {topic}\nTexto-base: {base_text}"}]},
        timeout=120)
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    data = json.loads(m.group(0))
    n = len(data["roteiro"].split())
    if not 60 <= n <= 180:
        raise ValueError(f"Roteiro com {n} palavras, fora do esperado")
    return data
