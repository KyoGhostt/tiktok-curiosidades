"""Voz (edge-tts, free) + legendas sincronizadas por palavra."""
import asyncio, edge_tts
from config import VOICE


async def _run(text, mp3, voice):
    com = edge_tts.Communicate(text, voice, rate="+8%", boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]))
    return words


def synth(text, mp3, voice=VOICE):
    return asyncio.run(_run(text, mp3, voice))


def _ts(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(w):
    return w.strip().strip('"\'()[]{}«»“”').rstrip(".,;:").upper()


def make_ass(words, path, script=None, per=3, overlays=()):
    """Legenda estilo TikTok: grupos de até 3 palavras, palavra falada em amarelo."""
    toks = script.split() if script else []
    disp = toks if len(toks) == len(words) else [w[2] for w in words]
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,"
            "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            "Style: Default,Montserrat ExtraBold,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,3,2,60,60,620,1\n"
            "Style: Badge,Montserrat ExtraBold,64,&H0000E5FF,&H0000E5FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,6,2,8,60,60,230,1\n"
            "Style: End,Montserrat ExtraBold,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,8,60,60,1450,1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")
    # grupos: quebra em pontuação final/vírgula ou ao chegar em `per` palavras
    groups, cur = [], []
    for i, d in enumerate(disp):
        if cur and sum(len(_clean(disp[j])) + 1 for j in cur) + len(_clean(d)) > 15:
            groups.append(cur); cur = []
        cur.append(i)
        if len(cur) >= per or d.endswith((".", "?", "!", ",", ":", ";")):
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    ev = []
    for gi, g in enumerate(groups):
        gend = words[groups[gi + 1][0]][0] if gi + 1 < len(groups) else words[g[-1]][1] + 0.3
        for k, wi in enumerate(g):
            st = words[wi][0]
            en = words[g[k + 1]][0] if k + 1 < len(g) else gend
            txt = " ".join(("{\\c&H0000E5FF&\\fscx112\\fscy112}" + _clean(disp[j]) + "{\\r}") if j == wi
                           else _clean(disp[j]) for j in g)
            ev.append(f"Dialogue: 0,{_ts(st)},{_ts(en)},Default,,0,0,0,,{txt}")
    end_t = words[-1][1] if words else 0
    for st, en, text, style in overlays:  # st/en: segundos; en=None => até o fim
        en = (end_t + 0.6) if en is None else en
        ev.append(f"Dialogue: 1,{_ts(max(st, 0))},{_ts(en)},{style},,0,0,0,,{text}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")
    return end_t
