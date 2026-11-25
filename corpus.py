"""Leitura do recorte brasileiro de avaliações da Steam (SBGames 2020)."""
import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "raw"
REVISION = "7d98f85588b2dac37658ea717054cb244b0ba87b"
BASE_URL = f"https://raw.githubusercontent.com/lucasvbalves/nlp-pt-br-datasets/{REVISION}/steam-reviews-portuguese-master/"
FILES = {
    "neg": "116bac97329491264052dd711725add006543ef02462568660a1824fcb7414bf",
    "pos": "48606c38c00a854ef833623851bf99eae2a05e95a489eb4795d756f1cb27bdf8",
}
LABELS = {0: "Não recomendou", 1: "Recomendou"}


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.\w+|(?<!\w)@\w+", " ", text, flags=re.I)
    return " ".join(text.split())


def load_reviews(download=True):
    rows = []
    for tag, expected in FILES.items():
        filename = f"steam_pt_{tag}.txt"
        path = DATA / filename
        if path.exists():
            raw = path.read_bytes()
        elif download:
            with urlopen(BASE_URL + filename, timeout=45) as response:
                raw = response.read()
        else:
            raise FileNotFoundError(path)
        raw = raw.replace(b"\r\n", b"\n")
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Conteúdo inesperado em {filename}. Confira a versão da base.")
        if not path.exists():
            DATA.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        for line, review in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
            rows.append((f"{tag}-{line:04}", clean(review), int(tag == "pos")))
    return pd.DataFrame(rows, columns=["id", "texto", "voto"])
