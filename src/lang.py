"""Configuração por idioma/canal. Escolha com a variável LANG_CODE (pt | en | es); padrão pt = canal original (inalterado).
Para voltar ao comportamento só-PT: não definir LANG_CODE."""
import os

CODE = os.environ.get("LANG_CODE", "pt").strip().lower() or "pt"

_PT_SUBS = ["AmItheAsshole", "pettyrevenge", "MaliciousCompliance", "TIFU", "entitledparents", "ProRevenge", "relationship_advice",
            "AITAH", "TrueOffMyChest", "JustNoMIL", "offmychest", "desabafos"]

CFG = {
    "pt": dict(
        nome="Curioso em Alta", canal="curiosoemalta", tz="America/Sao_Paulo", slots=[[12, 0], [17, 0], [20, 0]],
        voz={"m": "pt-BR-AntonioNeural", "f": "pt-BR-FranciscaNeural"}, ppm=200, avatar="avatar.png",
        subs=_PT_SUBS, idioma="português do Brasil", nomes="nomes brasileiros comuns",
        ui=dict(parte="PARTE {i} DE {n}", completa="HISTÓRIA COMPLETA", continua="CONTINUA NA PARTE {j}", gancho="A história continua",
                sufixo=" (Parte {i} de {n})", final="Final! O que você teria feito? Comenta! ", unico="O que você teria feito? Comenta! "),
        saudacao=r"^(gente|galera|pessoal|oi|ol[aá])\b[\s,!.:;-]*", e=" e ",
        fixas=["historiasdoreddit"],
    ),
    "en": dict(
        nome="Curious Trending", canal="curioustrending", tz="America/New_York", slots=[[12, 0], [18, 0], [21, 0]],
        voz={"m": "en-US-AndrewMultilingualNeural", "f": "en-US-AvaMultilingualNeural"}, ppm=175, avatar="avatar_US_vermelho.png",
        subs=["AmItheAsshole", "AITAH", "pettyrevenge", "MaliciousCompliance", "ProRevenge", "entitledparents", "TrueOffMyChest",
              "JustNoMIL", "offmychest", "BestofRedditorUpdates", "TalesFromRetail", "relationship_advice", "TIFU"],
        idioma="American English", nomes="common American first names",
        ui=dict(parte="PART {i} OF {n}", completa="FULL STORY", continua="CONTINUES IN PART {j}", gancho="The story continues",
                sufixo=" (Part {i} of {n})", final="Final part! What would you have done? Comment below! ", unico="What would you have done? Comment below! "),
        saudacao=r"^(hey|hi|hello|hey guys|hi guys|guys|everyone|what's up|so)\b[\s,!.:;-]*", e=" and ",
        fixas=["redditstories"], tagparte="part",
    ),
    "es": dict(
        nome="Curioso en Alza", canal="curiosoenalza", tz="America/Mexico_City", slots=[[12, 0], [18, 0], [21, 0]],
        voz={"m": "es-MX-JorgeNeural", "f": "es-MX-DaliaNeural"}, ppm=200, avatar="avatar_ES_verde.png",
        subs=["desahogo", "confesiones", "relatos"],   # ajustado pela sondagem (workflow sondar-subs)
        idioma="español latinoamericano neutro", nomes="nombres latinoamericanos comunes",
        ui=dict(parte="PARTE {i} DE {n}", completa="HISTORIA COMPLETA", continua="CONTINÚA EN LA PARTE {j}", gancho="La historia continúa",
                sufixo=" (Parte {i} de {n})", final="¡Final! ¿Qué habrías hecho? ¡Comenta! ", unico="¿Qué habrías hecho? ¡Comenta! "),
        saudacao=r"^(hola|oigan|gente|amigos|chicos|qué onda|que onda)\b[\s,!.:;-]*", e=" y ",
        fixas=["historiasdereddit"],
    ),
}
L = CFG[CODE]
UI = L["ui"]
