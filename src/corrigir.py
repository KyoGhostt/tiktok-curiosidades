"""Corrige hashtags erradas/repetidas das legendas JÁ geradas (EN/ES): reclassifica o tema pelo título e reescreve o texto dos posts
agendados no Buffer (só texto; horários nunca mudam) e dos pendentes do estoque. Uso: LANG_CODE=en python src/corrigir.py"""
import otimizar, otimo, fila, lang

c, f, log = otimo.load(), fila.load(), []
for s in f["stories"]:
    s["tema"] = otimo.classificar("", s["titulo"])
nodes = otimizar.coletar_posts()
otimizar.aplicar(c, f, nodes, False, log)
fila.save(f)
print(f"[{lang.CODE}]", " | ".join(log))
