"""Roteirista: LLM free via Hugging Face Inference Providers."""
import json, os, re, time, requests
from config import HF_TOKEN, LLM_MODEL

SYSTEM = """Você escreve roteiros curtos de curiosidades para TikTok em português do Brasil.
O vídeo pega carona num ASSUNTO EM ALTA no momento: o gancho (primeira frase, máx 14 palavras) deve citar o assunto
("Todo mundo está falando de X, mas você sabia...?") e o resto traz uma CURIOSIDADE factual ligada a ele.
Regras: 90 a 130 palavras no total, frases curtas, tom empolgado mas natural, use SOMENTE fatos presentes no
texto-base fornecido, nunca invente números, datas ou citações, termine com uma pergunta que gere comentários.
NEUTRALIDADE: foque em história, origem, como funciona, números do texto-base. Nunca dê opinião, não acuse, não elogie
nem critique pessoas vivas ou partidos, não faça previsões nem afirme quem está certo. Política pode ser tema, desde
que a curiosidade seja educativa e neutra (instituições, história, processos, símbolos, mecanismos).
Se o assunto envolver vítimas de tragédia, crime/violência, sexo ou drogas, ou o texto-base não tiver fatos
suficientes para uma curiosidade, responda APENAS {"rejeitar": true}.
Divida o roteiro em 5 a 7 CENAS (cada uma com 1 a 2 frases). Para cada cena, dê uma busca em inglês de
1 a 2 palavras (substantivos comuns) que descreva algo FILMÁVEL e CONCRETO ligado ao que a cena diz
(ex: "camera", "television", "laptop", "ocean", "microscope", "volcano"). Prefira cenas genéricas e comuns em bancos
de vídeo; nunca use nomes próprios nem "flag", "government", "army", "politics".
Para o TÍTULO: curto, curioso, com a palavra-chave do assunto em alta. HASHTAGS: 5, misturando a do assunto em alta
com as de nicho (curiosidades, voceSabia...), sem #.
Responda APENAS em JSON válido: {"titulo": str, "cenas": [{"texto": str, "busca": str}], "hashtags": [5 hashtags sem #]}"""

PLAN_SYSTEM = """Você é editor de um canal de curiosidades no TikTok Brasil. Recebe a lista de assuntos em alta agora
(com manchetes). Escolha UM assunto com bom potencial de curiosidade educativa, factual e neutra (história, origem,
como funciona), sobre o qual exista artigo na Wikipedia. Pode ser política, desde que o ângulo seja educativo (instituição,
processo, história, símbolo), nunca sobre disputas ou pessoas específicas. Evite tragédias com vítimas, crimes, sexo e drogas.
Responda APENAS em JSON: {"indice": int, "pesquisa": "termo curto em português para achar o artigo educativo na Wikipedia",
"angulo": "uma frase: a curiosidade que o vídeo vai explorar"}. Se nenhum servir: {"indice": -1}."""


class TopicRejected(Exception):
    pass


def providers():
    """Ordem de tentativa: todos com camada gratuita (OpenAI-compatível)."""
    out = []
    if os.environ.get("FREELLM_URL") and os.environ.get("FREELLM_KEY"):   # proxy FreeLLMAPI do dono (OpenAI-compatível); URL termina em /v1
        out.append(("freellm", os.environ["FREELLM_URL"].rstrip("/") + "/chat/completions", os.environ["FREELLM_KEY"],
                    os.environ.get("FREELLM_MODEL", "auto")))
    if os.environ.get("GROQ_API_KEY"):
        out.append(("groq", "https://api.groq.com/openai/v1/chat/completions", os.environ["GROQ_API_KEY"],
                    os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")))
    if os.environ.get("GEMINI_API_KEY"):
        out.append(("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY"], os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")))
        out.append(("gemini-lite", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY"], "gemini-2.5-flash-lite"))
    if os.environ.get("GEMINI_API_KEY_2"):    # 2ª chave Google AI Studio (outro projeto = outra cota)
        out.append(("gemini2", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    os.environ["GEMINI_API_KEY_2"], os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")))
    if os.environ.get("NVIDIA_API_KEY"):
        out.append(("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions", os.environ["NVIDIA_API_KEY"],
                    os.environ.get("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")))
    if os.environ.get("OPENROUTER_API_KEY"):
        out.append(("openrouter", "https://openrouter.ai/api/v1/chat/completions", os.environ["OPENROUTER_API_KEY"],
                    os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")))
    if HF_TOKEN:
        out.append(("hf", "https://router.huggingface.co/v1/chat/completions", HF_TOKEN, LLM_MODEL))
    return out


_VIVO = {}
_PREF = ("llama-3.3-70b", "llama-3.1-70b", "gpt-oss-120b", "qwen3-235b", "qwen2.5-72b", "qwen3-32b", "deepseek-v3", "deepseek-chat", "llama-4", "mistral-large", "gemma-3-27b")


def _descobrir(url, key, ruim):
    """Lista /models do provedor e escolhe o melhor modelo de texto disponivel (gratuito no OpenRouter)."""
    try:
        r = requests.get(url.replace("/chat/completions", "/models"), headers={"Authorization": f"Bearer {key}"}, timeout=30)
        ids = [m["id"] for m in r.json().get("data", []) if m.get("id") and m["id"] != ruim]
    except Exception:
        return None
    if "openrouter" in url: ids = [i for i in ids if i.endswith(":free")]
    for p in _PREF:
        for i in ids:
            if p in i.lower() and not any(x in i.lower() for x in ("vision", "embed", "guard", "whisper")): return i
    return None


def _chat(url, key, model, system, user, tokens=4096):
    body = {"model": model, "temperature": 0.8, "max_tokens": tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    model = _VIVO.get(url, model)
    body["model"] = model
    if "generativelanguage" in url: body["reasoning_effort"] = "none"   # gemini 2.5: o "pensar" gasta os tokens e a resposta JSON sai cortada
    r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=180, json=body)
    if r.status_code in (404, 410):    # modelo aposentado pelo provedor: descobre outro vivo em /models e tenta de novo
        novo = _descobrir(url, key, model)
        if novo:
            _VIVO[url] = novo; body["model"] = novo
            r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=180, json=body)
    if r.status_code == 400:      # alguns provedores não aceitam response_format: tenta sem (o JSON é extraído do texto)
        body.pop("response_format"); r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=180, json=body)
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt or "", re.S)
    if not m:
        raise ValueError("resposta sem JSON: " + (txt or "")[:80])
    return json.loads(m.group(0))


def _ask(url, key, model, topic, base_text, trend=None):
    ctx = ""
    if trend:
        ctx = (f"Assunto em alta agora: {trend['term']}. Manchetes: {'; '.join(trend.get('news', [])[:3])}\n"
               f"Ângulo: {trend.get('angulo', '')}\n")
    data = _chat(url, key, model, SYSTEM, f"{ctx}Tema do artigo: {topic}\nTexto-base: {base_text}")
    if data.get("rejeitar"):
        raise TopicRejected("tema rejeitado pelo filtro")
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


def plan_from_trends(trends):
    """Pede ao LLM para escolher o melhor assunto em alta e o ângulo de curiosidade."""
    lista = "\n".join(f"{i}. {t['term']} ({t['traffic']}) — {' | '.join(t['news'][:2])}" for i, t in enumerate(trends))
    for name, url, key, model in providers():
        try:
            d = _chat(url, key, model, PLAN_SYSTEM, lista, tokens=1500)
            i = int(d.get("indice", -1))
            if 0 <= i < len(trends) and d.get("pesquisa"):
                return {**trends[i], "pesquisa": d["pesquisa"], "angulo": d.get("angulo", "")}
            return None
        except Exception as e:
            print(f"plano falhou ({name}):", str(e)[:100])
    return None


def write_script(topic, base_text, trend=None):
    errs = []
    for name, url, key, model in providers():
        for attempt in range(3):
            try:
                return _ask(url, key, model, topic, base_text, trend)
            except TopicRejected:
                raise
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:120]}")
                time.sleep(8 * (attempt + 1))
                if "402" in str(e) or "401" in str(e) or "403" in str(e):
                    break
    raise RuntimeError("Nenhum LLM funcionou -> " + " | ".join(errs) if errs else
                       "Nenhuma chave de LLM configurada (GROQ_API_KEY, GEMINI_API_KEY ou HF_TOKEN)")
