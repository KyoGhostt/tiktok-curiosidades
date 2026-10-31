"""Histórias estilo Reddit: busca relatos (RSS público) ou cria história original; adapta para PT-BR em 3 a 6 partes."""
import html, json, random, re, requests, time
import xml.etree.ElementTree as ET
from config import OUT
import writer

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/atom+xml,application/xml,text/xml,*/*"}
SUBS = ["AmItheAsshole", "pettyrevenge", "MaliciousCompliance", "TIFU", "entitledparents", "ProRevenge", "relationship_advice",
        "AITAH", "TrueOffMyChest", "JustNoMIL", "offmychest", "desabafos"]   # desabafos = relatos em português (30/10)
PAUSA_S = 4   # o Reddit devolve 429 se os pedidos vierem rápido demais
HIST = OUT / "used_stories.json"
DEBUG = []

SYSTEM = """Você adapta histórias para vídeos narrados de TikTok no estilo "histórias do Reddit", em português do Brasil.
Narre em primeira pessoa, com linguagem falada brasileira natural e frases curtas. Troque nomes por nomes brasileiros comuns e
remova qualquer dado identificável (sobrenomes, cidades específicas, @, links, empresas reais). Mantenha os fatos do texto-base,
pode condensar, mas NÃO invente acontecimentos importantes. Se não houver texto-base, crie uma história ORIGINAL de drama
cotidiano (família, trabalho, vizinhos, amizade, relacionamento) com conflito e reviravolta.
@@DIVISAO@@ Corte em pontos de suspense: toda parte, menos a última,
termina num gancho forte; a parte 1 começa com um gancho forte, jogando o ouvinte direto no fato mais chocante ou numa frase de impacto (sem cumprimento: NUNCA comece nenhuma parte com "Gente", "Galera", "Pessoal", "Oi", "Olá" nem chame o público; varie a primeira frase de cada história); a última parte traz o desfecho e termina com uma pergunta que gere comentários.
ROTEIRO QUE PRENDE ATÉ O FIM (obrigatório): antes de escrever, defina uma PERGUNTA CENTRAL impactante, específica e intrigante (ex.: "o que ele
guardava no porão?", "quem mandou a mensagem?") que fica martelando na cabeça do ouvinte. Ela aparece nos primeiros segundos da parte 1,
ganha pistas e reviravoltas nas partes do meio SEM ser respondida, e só é respondida de verdade na última parte, com um desfecho que
surpreende e é coerente com tudo que veio antes (resposta genérica ou fraca é proibida). Cada parte: (1) abre já no fato mais forte, sem
preâmbulo; (2) tem um mini-arco próprio com uma virada no meio, para quem chegou agora entender; (3) planta no meio uma segunda dúvida
("mas o pior ainda estava por vir"); (4) termina com um gancho concreto sobre o que vem na próxima parte, nunca vago. A história precisa ter
um plot muito bom, com conflito forte, detalhes específicos e pelo menos uma reviravolta inesperada. Na última parte, inclua um detalhe
final que dê vontade de rever.
Rejeite com {"rejeitar": true} se envolver: menores de idade em situação sexual ou de abuso, violência gráfica, automutilação ou
suicídio, drogas pesadas, política ou partidos, discurso de ódio, ou pessoas públicas reais.
Responda APENAS em JSON válido: {"titulo": "título curto e chamativo, sem a palavra parte", "pergunta_central": "a pergunta intrigante da história", "genero_narrador": "m" ou "f",
"partes": [{"texto": str, "gancho_final": "4 a 8 palavras chamando para a próxima parte (vazio na última)"}, ... N itens],
"fundos": ["4 buscas em inglês de 1 a 2 palavras, de vídeo de fundo calmo, variado e com movimento, ex: rain window, night city, driving road, coffee shop"],
"tema": "UM destes, o que melhor descreve a história: trabalho, relacionamento, familia, vinganca, vizinhos, amizade, escola, drama"}"""


def _used():
    return set(json.loads(HIST.read_text())) if HIST.exists() else set()


def _mark(i):
    u = _used(); u.add(i); HIST.write_text(json.dumps(sorted(u)))


def _clean(c):
    t = re.sub(r"<[^>]+>", " ", html.unescape(c))
    t = re.sub(r"submitted by.*$", "", t, flags=re.S)
    t = re.sub(r"\[(link|comments)\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_posts(sub, kind="top"):
    """kind: top (mais votados da semana) ou controversial (mais polêmicos da semana)."""
    for tentativa in range(3):
        r = requests.get(f"https://www.reddit.com/r/{sub}/{kind}/.rss?t=week&limit=25", headers=UA, timeout=25)
        DEBUG.append(f"reddit r/{sub}/{kind}: http {r.status_code}")
        if r.status_code != 429:
            break
        time.sleep(12)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for pos, e in enumerate(ET.fromstring(r.content).findall("a:entry", ns)):
        link = e.find("a:link", ns).get("href")
        text = _clean(e.findtext("a:content", namespaces=ns) or "")
        out.append({"id": link, "sub": sub, "kind": kind, "pos": pos, "title": e.findtext("a:title", namespaces=ns) or "", "text": text})
    return out


def _nota(p):
    """Quanto mais polêmica e mais longa (= mais reviravoltas), melhor; topo do ranking também conta."""
    return (2.0 if p["kind"] == "controversial" else 0) + min(len(p["text"]), 7000) / 3500 - p["pos"] * 0.05 + random.random() * 0.8


def pick_story(n=3):
    """Até n relatos REAIS e novos, escolhidos entre os mais polêmicos/votados da semana de várias comunidades.
    Lista vazia => história original (só como último recurso). Para voltar ao modo antigo: git revert do commit 'Historias: ...'."""
    used, cands = _used(), []
    for sub in random.sample(SUBS, 5):
        for kind in ("top", "controversial"):
            try:
                cands += [p for p in fetch_posts(sub, kind) if 1800 <= len(p["text"]) <= 16000 and p["id"] not in used]
            except Exception as e:
                DEBUG.append(f"reddit r/{sub}/{kind}: erro {type(e).__name__} {str(e)[:80]}")
            time.sleep(PAUSA_S)
    vistos, uniq = set(), []
    for p in sorted(cands, key=_nota, reverse=True):
        if p["id"] not in vistos:
            vistos.add(p["id"]); uniq.append(p)
    return uniq[:n]


PPM = 240   # palavras narradas por minuto (voz do robô a +8%)


def plano(post=None):
    """Sorteia a duração de cada vídeo (1 a 5 min, por história) e calcula quantas partes o texto-base aguenta."""
    alvo = random.choice([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    if post:
        w = len(post["text"].split())
        n = max(1, min(6, round(w / (alvo * PPM))))
        pal = int(max(190, min(alvo * PPM, w * 0.95 / n)))   # nunca pede mais texto do que o relato real tem
    else:
        n = random.randint(2, 5)
        pal = int(alvo * PPM)
    return {"alvo_min": alvo, "n": n, "pal": pal}


def _divisao(pl):
    n, pal, alvo = pl["n"], pl["pal"], pl["alvo_min"]
    if n == 1:
        return (f"A história vira UM ÚNICO vídeo (1 parte), com cerca de {pal} palavras (≈ {pal/PPM:.1f} min narrado), sem ganchos de continuação: "
                f"ela abre com o gancho forte e fecha com o desfecho e uma pergunta que gere comentários.")
    return (f"Divida em EXATAMENTE {n} PARTES. Cada parte tem cerca de {pal} palavras (≈ {pal/PPM:.1f} min narrado; nunca fora de "
            f"{int(pal*0.8)} a {int(pal*1.2)}).")


def _validate(d, pl):
    ps = d.get("partes", [])
    if len(ps) != pl["n"]: raise ValueError(f"{len(ps)} partes (precisa de {pl['n']})")
    for i, p in enumerate(ps, 1):
        n = len(p["texto"].split())
        if not pl["pal"] * 0.7 <= n <= pl["pal"] * 1.35: raise ValueError(f"parte {i} com {n} palavras (alvo {pl['pal']})")
    if len(d.get("fundos", [])) < 2: raise ValueError("poucos fundos")
    d["_plano"] = pl
    return d


def write(post=None):
    """post=None => história original. Levanta writer.TopicRejected se o filtro recusar."""
    pl = plano(post)
    print(f"plano: {pl['n']} parte(s) de ~{pl['pal']} palavras (alvo {pl['alvo_min']} min)", flush=True)
    user = (f"Texto-base (r/{post['sub']}): {post['title']}\n\n{post['text'][:15000]}" if post
            else "Sem texto-base: crie uma história ORIGINAL no estilo AITA/histórias do Reddit.")
    system = SYSTEM.replace("@@DIVISAO@@", _divisao(pl))
    tokens = int(min(30000, max(8192, pl["n"] * pl["pal"] * 3.5)))
    errs = []
    for name, url, key, model in writer.providers():
        for attempt in range(3):
            try:
                d = writer._chat(url, key, model, system, user, tokens=tokens)
                if d.get("rejeitar"): raise writer.TopicRejected("rejeitada")
                return _validate(d, pl)
            except writer.TopicRejected:
                raise
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:100]}")
                writer.time.sleep(6 * (attempt + 1))
                if any(c in str(e) for c in ("401", "402", "403")): break
    raise RuntimeError("LLM falhou -> " + " | ".join(errs[-4:]))
