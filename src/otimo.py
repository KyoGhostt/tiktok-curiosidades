"""Configuração otimizada (horários e hashtags). Fica em estado/otimizacao.json e é reescrita todo dia por otimizar.py.
Quem agenda (fila.py), gera (main_story.py) ou calcula horários (schedule.py) só LÊ daqui."""
import json, os
from pathlib import Path

ARQ = Path(os.environ.get("ESTADO_DIR", "/tmp/estado")) / "otimizacao.json"
PADRAO_SLOTS = [[12, 0], [17, 0], [20, 0]]
FIXAS = ["historiasdoreddit"]          # sempre presentes (além de #parteN)
# hashtags reais em PT-BR por tema (a ordem é a prioridade inicial; os dados e a pesquisa reordenam)
POOL = {
    "trabalho": ["storytime", "chefe", "trabalho", "vidacorporativa", "historiasreais", "tretanotrabalho"],
    "relacionamento": ["storytime", "relacionamento", "casal", "casamento", "historiasreais", "marido"],
    "familia": ["storytime", "familia", "drama", "sogra", "historiasreais", "familiatreta"],
    "vinganca": ["storytime", "vinganca", "justica", "karma", "historiasreais", "vinganca"],
    "vizinhos": ["storytime", "vizinhos", "confusao", "tretas", "historiasreais", "vizinho"],
    "amizade": ["storytime", "amizade", "drama", "amigos", "historiasreais", "traicao"],
    "escola": ["storytime", "escola", "adolescencia", "colegio", "historiasreais", "bullying"],
    "drama": ["storytime", "drama", "historiasreais", "treta", "plottwist"],
}


def load():
    try:
        c = json.loads(ARQ.read_text())
    except Exception:
        c = {}
    c.setdefault("slots", PADRAO_SLOTS)
    c.setdefault("tags", {})            # tag -> {n, media} (views médias dos posts maduros que a usaram)
    c.setdefault("escolhidas", {})      # tema -> 3 hashtags variáveis decididas
    c.setdefault("candidatas", {})      # tema -> hashtags vindas da pesquisa na web
    c.setdefault("teste", None)         # teste de horário em andamento
    c.setdefault("base_n", 0)           # nº de posts maduros usados na última decisão de hashtags
    return c


def save(c):
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps(c, ensure_ascii=False, indent=1))


# hashtags que apareceram em vídeos de história com views muito acima da mediana do criador (vidIQ, 29/10) — entram no teste de todos os temas
GLOBAIS = ["historiasdetiktok"]


def pool(tema, c):
    seen, out = set(), []
    for t in POOL.get(tema, POOL["drama"]) + GLOBAIS + c.get("candidatas", {}).get(tema, []):
        if t not in seen:
            seen.add(t); out.append(t)
    return out


def tema_de(tags):
    """Descobre o tema de uma legenda pelas hashtags que ela já tem."""
    tags = set(tags)
    for tema, lst in POOL.items():
        if tema != "drama" and tags & set(lst[1:3]):
            return tema
    return "drama"


def variaveis(tema, c):
    ch = c["escolhidas"].get(tema)
    return ch if ch else pool(tema, c)[:3]


def hashtags(tema, parte, c=None):
    c = c or load()
    return [f"parte{parte}"] + FIXAS + variaveis(tema, c)       # 5 no total (limite útil do TikTok)


def legenda(titulo, parte, n, tema, c=None):
    cta = "" if parte < n else "Final! O que você teria feito? Comenta! "  # sem "Continua na parte N" (pedido do dono, 29/10)
    return f"{titulo} {cta}" + " ".join("#" + t for t in hashtags(tema, parte, c))


PALAVRAS = {"trabalho": ("chefe", "chefa", "equipe", "empresa", "trabalho", "emprego", "colega", "cliente", "funcion", "gerente"),
            "relacionamento": ("marido", "esposa", "namorad", "casamento", "casal", "aniversário", "noiv", "ex-", "traiç", "casar"),
            "familia": ("sogra", "mãe", "pai ", "irmã", "irmão", "família", "filho", "filha", "tia", "avó"),
            "vinganca": ("vingança", "vinganca", "revanche"),
            "vizinhos": ("vizinh",), "amizade": ("amig", "melhor amiga"), "escola": ("escola", "professor", "aluno", "colégio", "faculdade")}


def tema_por_titulo(titulo):
    t = titulo.lower()
    for tema, ps in PALAVRAS.items():
        if any(p in t for p in ps):
            return tema
    return None
