"""Histórias estilo Reddit: busca relatos (RSS público) ou cria história original; adapta para PT-BR em 3 a 6 partes."""
import html, json, random, re, requests, time
from pathlib import Path
import xml.etree.ElementTree as ET
from config import OUT
import writer, lang

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/atom+xml,application/xml,text/xml,*/*"}
SUBS = lang.L["subs"]   # PT: 12 comunidades (inclui r/desabafos); EN/ES: ver lang.py
PAUSA_S = 4   # o Reddit devolve 429 se os pedidos vierem rápido demais
HIST = OUT / "used_stories.json"   # por idioma: ESTADO_DIR/<lang> já separa (o workflow copia só o do idioma)
DEBUG = []

SYSTEM = """Você adapta histórias para vídeos narrados de TikTok no estilo "histórias do Reddit", em português do Brasil.
Narre em primeira pessoa, com linguagem falada brasileira natural e frases curtas. Mantenha os primeiros nomes comuns que já vêm no texto-base (ex.: João, Pedro, Letícia); só troque o nome se for estranho ao público ou raro. Remova
qualquer dado identificável (sobrenomes, cidades específicas, @, links, empresas reais). Mantenha os fatos do texto-base,
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


SYSTEM_I18N = """You adapt stories into narrated TikTok videos in the "Reddit stories" style, written in @@IDIOMA@@.
The source text is a real story told by a community member. Narrate in first person, in natural spoken @@IDIOMA@@ with short sentences.
Keep the common first names already in the source text (e.g. John, Emily, Maria); only swap a name if it is unusual or hard to pronounce, using @@NOMES@@. Remove any identifying data (surnames, specific cities, @handles, links, real companies). Keep the facts of the
source text; you may condense but do NOT invent important events. If there is no source text, create an ORIGINAL everyday-drama story
(family, work, neighbors, friendship, relationships) with conflict and a twist.
@@DIVISAO@@ Cut at suspense points: every part except the last ends on a strong hook; part 1 starts with a strong hook, throwing the listener straight into the most
shocking fact or an impact line (no greetings: NEVER open any part with "Hey", "Hi", "Guys", "Hello" or address the audience; vary the first sentence of each story);
the last part brings the resolution and ends with a question that invites comments.
STORY THAT HOLDS UNTIL THE END (mandatory): before writing, define a striking, specific, intriguing CENTRAL QUESTION (e.g. "what was he hiding in the basement?",
"who sent the message?") that keeps nagging at the listener. It appears in the first seconds of part 1, gains clues and twists in the middle parts WITHOUT being answered, and is only
truly answered in the last part with a surprising ending coherent with everything before (a generic or weak answer is forbidden). Each part: (1) opens on the strongest fact, no preamble;
(2) has its own mini-arc with a turn in the middle, so someone arriving now understands; (3) plants a second doubt midway ("but the worst was yet to come"); (4) ends with a concrete hook about
the next part, never vague. The story needs a really good plot, strong conflict, specific details and at least one unexpected twist. In the last part include a final detail that makes people want to rewatch.
Reject with {"rejeitar": true} if it involves: minors in sexual or abuse situations, graphic violence, self-harm or suicide, hard drugs, politics or parties, hate speech, or real public figures.
Answer ONLY with valid JSON (the text fields are in @@IDIOMA@@, the "fundos" searches in English): {"titulo": "short catchy title, without the word part", "pergunta_central": "the intriguing question of the story",
"genero_narrador": "m" or "f", "partes": [{"texto": str, "gancho_final": "4 to 8 words calling for the next part (empty in the last)"}, ... N items],
"fundos": ["4 English searches of 1-2 words for calm, varied, moving background video, e.g.: rain window, night city, driving road, coffee shop"],
"tema": "ONE of these, whichever best describes the story: trabalho, relacionamento, familia, vinganca, vizinhos, amizade, escola, drama"}"""


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
        r = requests.get(f"https://www.reddit.com/r/{sub}/{kind}/.rss?t={lang.L.get('periodo', 'week')}&limit=25", headers=UA, timeout=25)
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
    return ((2.0 if p["kind"] == "controversial" else 0) + min(len(p["text"]), 7000) / 3500 - p["pos"] * 0.05 + random.random() * 0.8
            + (3.0 if len(p["text"]) >= 5400 else 0))   # relato com ~1000+ palavras rende um vídeo de 5 min sem encher linguiça


def _banco():
    import os
    f = Path(os.environ.get("ESTADO_DIR", "/tmp/estado")) / "banco.json"
    try:
        used = _used()
        return [p for p in json.loads(f.read_text()) if p["id"] not in used]
    except Exception:
        return []


def pick_story(n=3):
    """Até n relatos REAIS e novos, escolhidos entre os mais polêmicos/votados da semana de várias comunidades.
    Lista vazia => história original (só como último recurso). Para voltar ao modo antigo: git revert do commit 'Historias: ...'."""
    used, cands = _used(), []
    cands += _banco()          # candidatos já guardados (banco.py) — sem depender do Reddit na hora
    if len(cands) >= n:
        vistos, uniq = set(), []
        for p in sorted(cands, key=_nota, reverse=True):
            if p["id"] not in vistos:
                vistos.add(p["id"]); uniq.append(p)
        DEBUG.append(f"banco: {len(cands)} candidatos")
        return uniq[:n]
    for sub in random.sample(SUBS, min(5, len(SUBS))):
        for kind in ("top", "controversial"):
            try:
                cands += [p for p in fetch_posts(sub, kind) if 2500 <= len(p["text"]) <= 20000 and p["id"] not in used]
            except Exception as e:
                DEBUG.append(f"reddit r/{sub}/{kind}: erro {type(e).__name__} {str(e)[:80]}")
            time.sleep(PAUSA_S)
    vistos, uniq = set(), []
    for p in sorted(cands, key=_nota, reverse=True):
        if p["id"] not in vistos:
            vistos.add(p["id"]); uniq.append(p)
    return uniq[:n]


PPM = lang.L["ppm"]   # palavras narradas por minuto com a voz em +8% (medido em 31/10: ~198 wpm; antes eu supunha 240)


ALVO_MIN = 5   # todo vídeo tem 5 minutos (pedido do dono, 31/10)


def plano(post=None):
    """Cada vídeo tem ~5 min (~1200 palavras). O nº de partes depende do tamanho do relato real."""
    pal = ALVO_MIN * PPM
    if post:
        w = len(post["text"].split())
        n = max(1, min(5, (w + 300) // pal))
    else:
        n = random.randint(1, 3)
    return {"alvo_min": ALVO_MIN, "n": n, "pal": pal}


def _divisao(pl):
    n, pal = pl["n"], pl["pal"]
    if lang.CODE != "pt":
        corpo = (f"Each part is a 5-minute narrated video: write about {pal} words per part (between {int(pal*0.92)} and {int(pal*1.08)}), pure story, no filler or repetition: "
                 "use every detail, line of dialogue, thought and context of the source text (without inventing important events) so the text reaches the requested length.")
        if n == 1:
            return "The story becomes ONE SINGLE video (1 part), with no continuation hooks: open with the strong hook and close with the resolution and a question that invites comments. " + corpo
        return f"Split it into EXACTLY {n} PARTS. " + corpo
    corpo = (f"Cada parte é um vídeo de 5 minutos narrados: escreva cerca de {pal} palavras por parte (entre {int(pal*0.92)} e {int(pal*1.08)}), "
             "pura história, sem enrolação nem repetição: aproveite todos os detalhes, falas, pensamentos e contexto do texto-base "
             "(sem inventar acontecimentos importantes) para o texto ter o tamanho pedido.")
    if n == 1:
        return ("A história vira UM ÚNICO vídeo (1 parte), sem ganchos de continuação: abre com o gancho forte e fecha com o desfecho "
                "e uma pergunta que gere comentários. " + corpo)
    return f"Divida em EXATAMENTE {n} PARTES. " + corpo


def _validate(d, pl):
    ps = d.get("partes", [])
    if len(ps) != pl["n"]: raise ValueError(f"{len(ps)} partes (precisa de {pl['n']})")
    for i, p in enumerate(ps, 1):
        n = len(p["texto"].split())
        if not pl["pal"] * 0.8 <= n <= pl["pal"] * 1.25: raise ValueError(f"parte {i} com {n} palavras (alvo {pl['pal']})")
    if len(d.get("fundos", [])) < 2: raise ValueError("poucos fundos")
    d["_plano"] = pl
    return d


def write(post=None):
    """post=None => história original. Levanta writer.TopicRejected se o filtro recusar."""
    pl = plano(post)
    print(f"plano: {pl['n']} parte(s) de ~{pl['pal']} palavras (alvo {pl['alvo_min']} min)", flush=True)
    user = (f"{'Texto-base' if lang.CODE == 'pt' else 'Source text'} (r/{post['sub']}): {post['title']}\n\n{post['text'][:20000]}" if post
            else ("Sem texto-base: crie uma história ORIGINAL no estilo AITA/histórias do Reddit." if lang.CODE == "pt"
            else "No source text: create an ORIGINAL story in the AITA / Reddit stories style."))
    system = (SYSTEM if lang.CODE == "pt" else SYSTEM_I18N.replace("@@IDIOMA@@", lang.L["idioma"]).replace("@@NOMES@@", lang.L["nomes"])).replace("@@DIVISAO@@", _divisao(pl))
    tokens = int(min(30000, max(8192, pl["n"] * pl["pal"] * 3.5)))
    errs = []
    user0, fb = user, ""
    for name, url, key, model in writer.providers():
        for attempt in range(4):
            try:
                d = writer._chat(url, key, model, system, user0 + fb, tokens=tokens)
                if d.get("rejeitar"): raise writer.TopicRejected("rejeitada")
                return _validate(d, pl)
            except writer.TopicRejected:
                raise
            except Exception as e:
                errs.append(f"{name}: {type(e).__name__} {str(e)[:100]}")
                if isinstance(e, ValueError) and ("palavras" in str(e) or "partes" in str(e)):   # devolve o erro ao modelo para ele corrigir o tamanho
                    fb = f"\n\nPREVIOUS ATTEMPT REJECTED: {e}. Fix exactly this: respect the number of parts and write FULL-length parts (every part about {pl['pal']} words; count them); do not shorten."
                writer.time.sleep(6 * (attempt + 1))
                if any(c in str(e) for c in ("401", "402", "403")): break
    raise RuntimeError("LLM falhou -> " + " | ".join(errs[-4:]))
