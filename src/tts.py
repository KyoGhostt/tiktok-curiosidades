"""Voz (edge-tts, free) + legendas sincronizadas por palavra."""
import asyncio, edge_tts
from config import VOICE


async def _run(text, mp3):
    com = edge_tts.Communicate(text, VOICE, rate="+8%")
    words = []
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]))
    return words


def synth(text, mp3):
    return asyncio.run(_run(text, mp3))


def _ts(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def make_ass(words, path, per=3):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BorderStyle,Outline,Shadow,Alignment,MarginV\n"
            "Style: Default,DejaVu Sans,78,&H00FFFFFF,&H00000000,1,6,0,2,520\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Text\n")
    lines = []
    for i in range(0, len(words), per):
        g = words[i:i + per]
        end = words[i + per][0] if i + per < len(words) else g[-1][1]
        lines.append(f"Dialogue: 0,{_ts(g[0][0])},{_ts(end)},Default,{' '.join(w[2] for w in g).upper()}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")
    return words[-1][1] if words else 0
