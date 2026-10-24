"""Roteirista: LLM free via Hugging Face Inference Providers."""
import json, os, re, time, requests
from config import HF_TOKEN, LLM_MODEL

SYSTEM = """Você escreve roteiros curtos de curiosidades para TikTok em português do Brasil.
Regras: gancho forte na primeira frase (máx 12 palavras), 90 a 130 palavras no total,
frases curtas, tom empolgado mas natural, use SOMENTE fatos presentes no texto-base fornecido,
nunca invente números ou datas, termine com uma pergunta que gere comentários.
Divida o roteiro em 5 a 7 CENAS (cada uma com 1 a 2 frases). Para cada cena, dê uma busca em inglês de
2 a 3 palavras que descreva algo FILMÁVEL e CONCRETO que apareça no vídeo de fundo, ligado ao que a cena diz
(ex: "video camera", "old television", "laptop typing", "ocean waves"). Nunca use nomes próprios,
marcas ou conceitos abstratos nas buscas.
Responda APENAS em JSON válido: {"titulo": str, "cenas": [{"texto": str, "busca": str}], "hashtags": [5 hashtags sem #]}"""


def providers():
    """Ordem de tentativa: todos com camada gratuita (OpenAI-compatível)."""
    out = []
    if os.environ.get("GROQ_API_KEY"):
        out.append(("groq", "https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"],
                    os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")))
    if os.environ.get("GEMINI_API_KEY"):
        out.append(("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY"], os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")))
        out.append(("gemini-lite", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY"], "gemini-2.5-flash-lite"))
    if HF_TOKEN:
        out.append(("hf", "https://router.huggingface.co/v1/chat/completions", HF_TOKEN, LLM_MODEL))
    return out


def _ask(url, key, model, topic, base_text):
    r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=120,
        json={"model": model, "temperature": 0.8, "max_tokens": 4096, "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": SYSTEM},
                           {"role": "user", "content": f"Tema: {topic}\nTexto-base: {base_text}"}]})
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt or "", re.S)
    if not m:
        raise ValueError("resposta sem JSON: " + (txt or "")[:80])
    data = json.loads(m.group(0))
    cenas = [c for c in data.get("cenas", []) if c.get("texto") and c.get("busca")]
    if len(cenas) < 3:
        raise ValueError("menos de 3 cenas")
    data["cenas"] = cenas
    data["roteiro"] = " ".join(c["texto"].strip() for c in cenas)
    data["palavras_chave_busca"] = [c["busca"] for c in cenas]
    n = len(data["roteiro"].split())
    if not 60 <= n <= 180:
        raise ValueError(f"Roteiro com {n} palavras, fora do esperado")
    return data


def write_script(topic, base_text):
    errs = []
    for name, url, key, model in providers():
        for attempt in range(3):
            try:
                return _ask(url, key, model, topic, base_text)
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:120]}")
                time.sleep(8 * (attempt + 1))
                if "402" in str(e) or "401" in str(e) or "403" in str(e):
                    break
    raise RuntimeError("Nenhum LLM funcionou -> " + " | ".join(errs) if errs else
                       "Nenhuma chave de LLM configurada (GROQ_API_KEY, GEMINI_API_KEY ou HF_TOKEN)")
