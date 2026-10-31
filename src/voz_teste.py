"""Teste de vozes: gera 1 vídeo curto por voz (Gemini TTS + voz atual do edge-tts) com o mesmo texto, fundo e legenda do robô."""
import base64, os, random, subprocess, sys, wave
from pathlib import Path
import requests
import tts, video, capa, mc

OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
W = Path("/tmp/vt"); W.mkdir(exist_ok=True)
KEY = os.environ.get("GEMINI_API_KEY", "")
TEXTO = ("Eu tinha vinte e quatro anos quando descobri que a minha própria família guardava um segredo sobre mim. "
         "Tudo começou numa quinta-feira, quando minha mãe me ligou chorando e pediu que eu fosse até a casa dela, sozinha. "
         "Eu estranhei, porque ela nunca pedia nada. Quando cheguei, meu pai estava sentado na cozinha, de cabeça baixa, "
         "e havia uma caixa velha em cima da mesa. Minha mãe respirou fundo e disse: abre. "
         "Dentro da caixa tinha uma pilha de cartas, todas endereçadas a mim, todas com a mesma letra. "
         "A letra era da minha avó, a mesma avó que, segundo eles, tinha morrido sem nunca querer saber de mim. "
         "Peguei a primeira carta com a mão tremendo e comecei a ler. Na terceira linha, eu parei de respirar. "
         "Porque ali estava escrito o motivo de tudo, e ele mudava completamente a minha história.")
# (nome do exemplo do dono, voz Gemini candidata, estilo)
VOZES = [("kroma_homem", "Orus", "em ritmo rápido e envolvente, como um contador de histórias de TikTok"),
         ("sublime_homem", "Puck", "em ritmo rápido, jovem e animado, como um contador de histórias de TikTok"),
         ("viciado_homem_grave", "Charon", "em ritmo rápido, voz grave e tensa, como um contador de histórias de TikTok"),
         ("h775_mulher", "Kore", "em ritmo calmo e envolvente, voz feminina suave, como uma contadora de histórias")]


def gemini(voz, estilo, mp3):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
    body = {"contents": [{"parts": [{"text": f"Leia em português do Brasil, {estilo}, com emoção e variando o tom:\n{TEXTO}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    for t in range(3):
        r = requests.post(url, headers={"x-goog-api-key": KEY}, json=body, timeout=180)
        if r.status_code == 200: break
        print("  gemini", r.status_code, r.text[:200]); 
        if r.status_code == 429: __import__("time").sleep(30)
    r.raise_for_status()
    pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    raw = W / "g.pcm"; raw.write_bytes(pcm)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(raw), str(mp3)], check=True)


def palavras(mp3):
    from faster_whisper import WhisperModel
    global _wm
    try: _wm
    except NameError: _wm = WhisperModel("small", device="cpu", compute_type="int8")
    import numpy as np, librosa
    y, _ = librosa.load(str(mp3), sr=16000)
    segs, _i = _wm.transcribe(y.astype("float32"), language="pt", beam_size=1, word_timestamps=True)
    return [(w.start, w.end, w.word.strip()) for s in segs for w in s.words]


def montar(nome, mp3, words, clip):
    ass = W / f"{nome}.ass"
    dur = tts.make_ass(words, ass, script=None, overlays=[(0, None, "TESTE DE VOZ", "Badge")])
    total = dur + 0.6
    card = capa.card(W / f"{nome}.png", "Teste de voz: " + nome.replace("_", " "), "x", "x", 1, 1)
    full = W / f"{nome}_full.mp4"
    video.build_mc(clip[0], random.uniform(0, max(1, clip[1] - total)), total, mp3, ass, full, card, calmo=False)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(full), "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "30", "-c:a", "aac", "-b:a", "96k", str(OUT / f"voz-{nome}.mp4")], check=True)
    full.unlink(missing_ok=True)


clip = mc.pick_minecraft()
print("fundo:", clip and clip[0].name)
for nome, voz, estilo in VOZES:
    try:
        mp3 = W / f"{nome}.mp3"
        gemini(voz, estilo, mp3)
        w = palavras(mp3)
        print(f"{nome}: voz {voz}, {len(w)} palavras, {w[-1][1]:.0f}s", flush=True)
        montar(nome, mp3, w, clip)
    except Exception as e:
        print(f"{nome}: FALHOU {type(e).__name__} {str(e)[:200]}", flush=True)
# voz atual do robô (edge-tts) para comparar
try:
    mp3 = W / "atual_mulher.mp3"
    w = tts.synth(tts.limpar_texto(TEXTO), mp3, "pt-BR-FranciscaNeural")
    montar("atual_Francisca_mulher", mp3, w, clip)
    mp3 = W / "atual_homem.mp3"
    w = tts.synth(tts.limpar_texto(TEXTO), mp3, "pt-BR-AntonioNeural")
    montar("atual_Antonio_homem", mp3, w, clip)
    print("vozes atuais ok")
except Exception as e:
    print("edge FALHOU", repr(e)[:200])
