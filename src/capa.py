"""Cartão de abertura (estilo história do Reddit) que aparece nos primeiros segundos e vira a capa do vídeo."""
import hashlib, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ["/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf",
         "/usr/share/fonts/opentype/montserrat/Montserrat-ExtraBold.otf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
PALETA = [(255, 45, 135), (255, 140, 0), (0, 170, 255), (130, 90, 255), (0, 190, 120), (240, 60, 60)]


def _font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            continue
    return ImageFont.load_default()


def cor(titulo):
    return PALETA[int(hashlib.md5(titulo.encode()).hexdigest(), 16) % len(PALETA)]


def gancho(texto, limite=230):
    """Primeiras frases do texto, até ~limite caracteres, terminando em ponto final."""
    t = re.sub(r"\s+", " ", texto).strip()
    if len(t) <= limite:
        return t
    cut = t[:limite]
    m = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[:m + 1] if m > 80 else cut.rsplit(" ", 1)[0] + "…")


def _wrap(d, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + ([cur] if cur else [])


def card(path, titulo, sub, texto, parte, n, nome="Curioso em Alta"):
    """Cartão de abertura: avatar + nome com selo azul + TÍTULO da história (não o texto que a voz lê)."""
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cw, pad, x0 = 940, 44, 70
    fb, fn, fs = _font(64), _font(52), _font(30)
    tit = titulo.strip().rstrip(".")
    lines = _wrap(d, tit, fb, cw - 2 * pad)[:5]
    head_h = 130
    lh = 80
    ch = pad + head_h + 30 + len(lines) * lh + pad
    y0 = 560
    c = cor(titulo)
    d.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), radius=48, fill=(255, 255, 255, 255), outline=c + (255,), width=14)
    try:
        av = Image.open(ROOT / "assets" / "avatar.png").convert("RGBA").resize((head_h, head_h))
        m = Image.new("L", (head_h, head_h), 0); ImageDraw.Draw(m).ellipse((0, 0, head_h, head_h), fill=255)
        img.paste(av, (x0 + pad, y0 + pad), m)
    except Exception:
        d.ellipse((x0 + pad, y0 + pad, x0 + pad + head_h, y0 + pad + head_h), fill=c + (255,))
    tx = x0 + pad + head_h + 24
    d.text((tx, y0 + pad + 4), nome, font=fn, fill=(20, 20, 20, 255))
    bx = tx + d.textlength(nome, font=fn) + 16          # selo de verificado (círculo azul com check)
    d.ellipse((bx, y0 + pad + 14, bx + 44, y0 + pad + 58), fill=(29, 155, 240, 255))
    d.line((bx + 11, y0 + pad + 37, bx + 20, y0 + pad + 46, bx + 34, y0 + pad + 26), fill=(255, 255, 255, 255), width=6)
    d.text((tx, y0 + pad + 74), f"PARTE {parte} DE {n}", font=fs, fill=(110, 110, 110, 255))
    y = y0 + pad + head_h + 30
    for ln in lines:
        d.text((x0 + pad, y), ln, font=fb, fill=(15, 15, 15, 255))
        y += lh
    img.save(path)
    return path
