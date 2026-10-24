"""Roteirista: LLM free via Hugging Face Inference Providers."""
import json, os, re, requests
from config import HF_TOKEN, LLM_MODEL

SYSTEM = """Você escreve roteiros curtos de curiosidades para TikTok em português do Brasil.
Regras: gancho forte na primeira frase (máx 12 palavras), 90 a 130 palavras no total,
frases curtas, tom empolgado mas natural, use SOMENTE fatos presentes no texto-base fornecido,
nunca invente números ou datas, termine com uma pergunta que gere comentários.
Responda APENAS em JSON válido: {"titulo": str, "roteiro": str, "palavras_chave_busca": [3 termos em inglês para buscar vídeos de fundo], "hashtags": [5 hashtags sem #]}"""


def providers():
    """Ordem de tentativa: todos com camada gratuita (OpenAI-compatível)."""
    out = []
    if os.environ.get("GROQ_API_KEY"):
        out.append(("groq", "https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"],
                    os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")))
    if os.environ.get("GEMINI_API_KEY"):
        out.append(("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY"], os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")))
    if HF_TOKEN:
        out.append(("hf", "https://router.huggingface.co/v1/chat/completions", HF_TOKEN, LLM_MODEL))
    return out


def _ask(url, key, model, topic, base_text):
    r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=120,
        json={"model": model, "temperature": 0.8, "max_tokens": 900,
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": f"Tema: {topic}\nTexto-base: {base_text}"}]})
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    data = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    n = len(data["roteiro"].split())
    if not 60 <= n <= 180:
        raise ValueError(f"Roteiro com {n} palavras, fora do esperado")
    return data


def write_script(topic, base_text):
    errs = []
    for name, url, key, model in providers():
        for _ in range(2):
            try:
                return _ask(url, key, model, topic, base_text)
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:120]}")
                if "402" in str(e) or "401" in str(e) or "403" in str(e):
                    break
    raise RuntimeError("Nenhum LLM funcionou -> " + " | ".join(errs) if errs else
                       "Nenhuma chave de LLM configurada (GROQ_API_KEY, GEMINI_API_KEY ou HF_TOKEN)")
