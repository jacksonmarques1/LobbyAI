"""Coleta reproduzível dos indicadores mostrados na página de descoberta."""
import json
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "data" / "catalogo.json"
GAMES = [
    (1145350, "Hades II", "Roguelike", "Solo", "Enfrente o titã do tempo numa sequência de combates, feitiços e novas tentativas."),
    (548430, "Deep Rock Galactic", "Tiro em equipe", "Cooperativo", "Quatro anões, uma missão de mineração e cavernas que mudam a cada descida."),
    (2379780, "Balatro", "Estratégia", "Solo", "Combine curingas e mãos de pôquer para quebrar o placar da próxima rodada."),
    (753640, "Outer Wilds", "Exploração", "Solo", "Explore um sistema solar preso em um ciclo de 22 minutos. Cada descoberta muda sua próxima viagem."),
    (1030300, "Hollow Knight: Silksong", "Aventura", "Solo", "Suba por um reino de seda e canções com a agulha e a agilidade de Hornet."),
    (632360, "Risk of Rain 2", "Roguelike", "Cooperativo", "Sobreviva a um planeta que fica mais hostil a cada minuto, sozinho ou em equipe."),
    (892970, "Valheim", "Sobrevivência", "Cooperativo", "Construa um abrigo e atravesse mares desconhecidos com seu grupo de vikings.",),
    (646570, "Slay the Spire", "Estratégia", "Solo", "Monte um baralho carta por carta enquanto escolhe sua rota até o topo da torre."),
]


def fetch(url):
    request = Request(url, headers={"User-Agent": "LobbyAI/1.1"})
    with urlopen(request, timeout=15) as response:
        return response.read()


def collect(entry, old):
    appid, title, genre, mode, summary = entry
    cdn = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}"
    item = dict(old, id=appid, title=title, genre=genre, mode=mode, summary=summary,
                cover=f"{cdn}/header.jpg", hero=f"{cdn}/library_hero.jpg")
    for metric, url in [
        ("players", f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"),
        ("reviews", f"https://steamspy.com/api.php?request=appdetails&appid={appid}")]:
        try:
            payload = json.loads(fetch(url))
            if metric == "players":
                data = payload["response"]
                if data.get("result") != 1:
                    raise ValueError("contagem indisponível")
                value = {"count": int(data["player_count"])}
            else:
                if int(payload["appid"]) != appid:
                    raise ValueError("jogo divergente")
                value = {k: int(payload[k]) for k in ("positive", "negative")}
            value["consultado"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            item[metric] = value
        except (OSError, ValueError, KeyError) as exc:
            print(f"{title} / {metric}: {exc}")
    return item


def refresh():
    old = {g["id"]: g for g in json.loads(SNAPSHOT.read_text("utf-8"))} if SNAPSHOT.exists() else {}
    items = []
    for entry in GAMES:
        items.append(collect(entry, old.get(entry[0], {})))
        sleep(1)
    tmp = SNAPSHOT.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SNAPSHOT)


if __name__ == "__main__":
    refresh()
