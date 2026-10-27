"""Histórias estilo Reddit: busca relatos (RSS público) ou cria história original; adapta para PT-BR em 3 a 6 partes."""
import html, json, random, re, requests
import xml.etree.ElementTree as ET
from config import OUT
import writer

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/atom+xml,application/xml,text/xml,*/*"}
SUBS = ["AmItheAsshole", "pettyrevenge", "MaliciousCompliance", "TIFU", "entitledparents", "ProRevenge", "relationship_advice"]
HIST = OUT / "used_stories.json"
DEBUG = []

SYSTEM = """Você adapta histórias para vídeos narrados de TikTok no estilo "histórias do Reddit", em português do Brasil.
Narre em primeira pessoa, com linguagem falada brasileira natural e frases curtas. Troque nomes por nomes brasileiros comuns e
remova qualquer dado identificável (sobrenomes, cidades específicas, @, links, empresas reais). Mantenha os fatos do texto-base,
pode condensar, mas NÃO invente acontecimentos importantes. Se não houver texto-base, crie uma história ORIGINAL de drama
cotidiano (família, trabalho, vizinhos, amizade, relacionamento) com conflito e reviravolta.
Divida em N PARTES, com N entre 3 e 6 (história curta = 3; média = 4; longa e cheia de reviravoltas = 5 ou 6; nunca mais de 6).
Cada parte tem de 190 a 260 palavras (cerca de 1 min a 1 min40 narrado), cortando em pontos de suspense: toda parte, menos a última,
termina num gancho forte; a parte 1 começa com um gancho forte; a última parte traz o desfecho e termina com uma pergunta que gere comentários.
Rejeite com {"rejeitar": true} se envolver: menores de idade em situação sexual ou de abuso, violência gráfica, automutilação ou
suicídio, drogas pesadas, política ou partidos, discurso de ódio, ou pessoas públicas reais.
Responda APENAS em JSON válido: {"titulo": "título curto e chamativo, sem a palavra parte", "genero_narrador": "m" ou "f",
"partes": [{"texto": str, "gancho_final": "4 a 8 palavras chamando para a próxima parte (vazio na última)"}, ... N itens],
"fundos": ["4 buscas em inglês de 1 a 2 palavras, de vídeo de fundo calmo, variado e com movimento, ex: rain window, night city, driving road, coffee shop"],
"hashtags": ["4 hashtags específicas da história, sem #"]}"""


def _used():
    return set(json.loads(HIST.read_text())) if HIST.exists() else set()


def _mark(i):
    u = _used(); u.add(i); HIST.write_text(json.dumps(sorted(u)))


def _clean(c):
    t = re.sub(r"<[^>]+>", " ", html.unescape(c))
    t = re.sub(r"submitted by.*$", "", t, flags=re.S)
    t = re.sub(r"\[(link|comments)\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_posts(sub):
    r = requests.get(f"https://www.reddit.com/r/{sub}/top/.rss?t=week&limit=25", headers=UA, timeout=25)
    DEBUG.append(f"reddit r/{sub}: http {r.status_code}")
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        link = e.find("a:link", ns).get("href")
        text = _clean(e.findtext("a:content", namespaces=ns) or "")
        out.append({"id": link, "sub": sub, "title": e.findtext("a:title", namespaces=ns) or "", "text": text})
    return out


def pick_story(n=3):
    """Até n relatos novos entre os MAIS POPULARES da semana (o RSS 'top' já vem ordenado por votos).
    Lista vazia => usar história original."""
    used, cands = _used(), []
    for sub in random.sample(SUBS, len(SUBS)):
        try:
            ok = [p for p in fetch_posts(sub) if 1500 <= len(p["text"]) <= 9000 and p["id"] not in used]
            cands += ok[:6]  # só o topo do ranking de cada subreddit
        except Exception as e:
            DEBUG.append(f"reddit r/{sub}: erro {type(e).__name__} {str(e)[:80]}")
        if len(cands) >= n * 2:
            break
    random.shuffle(cands)
    return cands[:n]


def _validate(d):
    ps = d.get("partes", [])
    if not 3 <= len(ps) <= 6: raise ValueError(f"{len(ps)} partes (precisa de 3 a 6)")
    for i, p in enumerate(ps, 1):
        n = len(p["texto"].split())
        if not 150 <= n <= 290: raise ValueError(f"parte {i} com {n} palavras")
    if len(d.get("fundos", [])) < 2: raise ValueError("poucos fundos")
    return d


def write(post=None):
    """post=None => história original. Levanta writer.TopicRejected se o filtro recusar."""
    user = (f"Texto-base (r/{post['sub']}): {post['title']}\n\n{post['text'][:9000]}" if post
            else "Sem texto-base: crie uma história ORIGINAL no estilo AITA/histórias do Reddit.")
    errs = []
    for name, url, key, model in writer.providers():
        for attempt in range(3):
            try:
                d = writer._chat(url, key, model, SYSTEM, user, tokens=8192)
                if d.get("rejeitar"): raise writer.TopicRejected("rejeitada")
                return _validate(d)
            except writer.TopicRejected:
                raise
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:100]}")
                writer.time.sleep(6 * (attempt + 1))
                if any(c in str(e) for c in ("401", "402", "403")): break
    raise RuntimeError("LLM falhou -> " + " | ".join(errs[-4:]))
