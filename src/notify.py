"""Manda o pacote da história (resumo + 3 vídeos com legenda e horário) e guarda os file_ids para os lembretes."""
import json, sys
from pathlib import Path
import telegram


def deliver(d):
    d = Path(d)
    info = json.loads((d / "info.json").read_text())
    linhas = [f"📚 Nova história: {info['titulo']}", f"({info['origem']})", "", "📅 Cronograma (horário de Brasília):"]
    linhas += [f"• Parte {p['parte']}/3: {p['quando']}" for p in info["partes"]]
    linhas += ["", "Os 3 vídeos vêm logo abaixo. No horário de cada parte eu te lembro e reenvio o vídeo.",
               "Ao postar, marque “conteúdo gerado por IA”. Segure a legenda para copiar."]
    telegram.send_message("\n".join(linhas))
    for p in info["partes"]:
        cap = f"🎬 PARTE {p['parte']}/3 — postar {p['quando']}\n\n{p['legenda']}"
        p["file_id"] = telegram.send_video(d / p["arquivo"], cap, duration=p.get("duracao_s", 0), silent=True)
        print(f"telegram: parte {p['parte']} enviada")
    (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    deliver(sys.argv[1])
