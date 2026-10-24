import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

HF_TOKEN = os.environ.get("HF_TOKEN", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
# Modelo free via Hugging Face Inference Providers (troque se sair do ar)
LLM_MODEL = os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-72B-Instruct")
VOICE = os.environ.get("TTS_VOICE", "pt-BR-AntonioNeural")
VIDEOS_PER_RUN = int(os.environ.get("VIDEOS_PER_RUN", "1"))
