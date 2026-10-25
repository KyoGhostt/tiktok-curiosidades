"""Cofre de tokens do TikTok: dataset PRIVADO no Hugging Face (o repo do GitHub é público, nada de segredo nele)."""
import json, os
from huggingface_hub import HfApi, hf_hub_download

REPO = os.environ.get("STATE_REPO", "kyoghostt/curioso-state")
FILE = "tiktok.json"


def _tok():
    return os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")


def load(name=FILE):
    try:
        p = hf_hub_download(REPO, name, repo_type="dataset", token=_tok(), force_download=True)
        return json.load(open(p))
    except Exception as e:
        print("cofre sem tokens:", type(e).__name__)
        return None


def save(data, name=FILE):
    api = HfApi(token=_tok())
    api.create_repo(REPO, repo_type="dataset", private=True, exist_ok=True)
    api.upload_file(path_or_fileobj=json.dumps(data).encode(), path_in_repo=name, repo_id=REPO, repo_type="dataset",
                    commit_message="atualiza tokens")
