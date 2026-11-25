"""Coleta reproduzível dos indicadores mostrados na página de descoberta."""
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from html import unescape
import re

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
    item = dict(id=appid, title=title, genre=genre, mode=mode, summary=summary,
                cover=f"{cdn}/header.jpg", hero=f"{cdn}/library_hero.jpg")
    item.update(old)
    item.update(genre=genre, summary=summary or old.get("summary", ""))
    try:
        store = json.loads(fetch(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=brazilian"))[str(appid)]
        if not store.get("success"):
            raise ValueError("ficha indisponível")
        details = store["data"]
        categories = {c["id"] for c in details.get("categories", [])}
        item.update(title=details["name"], indie=any(g["id"] == "23" for g in details.get("genres", [])),
                    free=bool(details["is_free"] and not details.get("release_date", {}).get("coming_soon")), solo=2 in categories, coop=bool(categories & {9, 38, 39}),
                    online_coop=38 in categories, local_coop=39 in categories,
                    demos=[d["appid"] for d in details.get("demos", []) if d.get("appid")],
                    developer=", ".join(details.get("developers", [])), cover=details["header_image"],
                    store_checked=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if not summary:
            item["summary"] = " ".join(unescape(re.sub(r"<[^>]*>", "", details.get("short_description", ""))).split())
            item["genre"] = next((g["description"] for g in details.get("genres", []) if g["id"] not in {"23","37","70"}), "Indie")
        modes = [text for flag, text in [(item["solo"], "Solo"), (item["coop"], "Cooperativo")] if flag]
        item["mode"] = " + ".join(modes) or "Multijogador"
    except (OSError, ValueError, KeyError) as exc:
        print(f"{appid} / loja: {exc}")
        if not old:
            return None
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


DEMO_FEED = ("https://store.steampowered.com/search/results/?start=0&count=24&sort_by=Released_DESC"
             "&category1=10&tags=492&infinite=1&cc=br&l=brazilian")


def recent_demos():
    """A busca retorna o ID da demo; a ficha confirma o vínculo com o jogo."""
    page = json.loads(fetch(DEMO_FEED))["results_html"]
    ids = dict.fromkeys(re.findall(r'data-ds-appid="(\d+)"', page))
    found = {}
    for appid in ids:
        try:
            listing = json.loads(fetch(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=brazilian"))[appid]
            demo = listing.get("data", {})
            parent = int(demo.get("fullgame", {}).get("appid", 0))
            if demo.get("type") == "demo" and parent and demo.get("platforms", {}).get("windows"):
                found[parent] = int(appid)
        except (OSError, ValueError, KeyError):
            continue
        if len(found) == 8:
            break
    return found


def refresh():
    old = {g["id"]: g for g in json.loads(SNAPSHOT.read_text("utf-8"))} if SNAPSHOT.exists() else {}
    from concurrent.futures import ThreadPoolExecutor
    entries = {row[0]: row for row in GAMES}
    for appid, genre, summary in json.loads((ROOT / "data/selecao.json").read_text("utf-8")):
        entries.setdefault(appid, (appid, "", genre, "", summary))
    try:
        recent = recent_demos()
    except (OSError, ValueError, KeyError):
        recent = {}
    if not recent:
        recent = {g["id"]: g["demos"][0] for g in old.values() if g.get("from_feed") and g.get("demos")}
    for appid in recent:
        entries.setdefault(appid, (appid, "", "Indie", "", ""))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = pool.map(lambda row: collect(row, old.get(row[0], {})), entries.values())
        items = [item for item in results if item]
    for game in items:
        game["from_feed"] = game["id"] in recent
        if game["from_feed"]:
            demo = recent[game["id"]]
            game["demos"] = [demo] + [d for d in game.get("demos", []) if d != demo]
    if not items:
        raise RuntimeError("A coleta não encontrou jogos disponíveis.")
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=SNAPSHOT.parent, delete=False) as out:
        json.dump(items, out, ensure_ascii=False, indent=2)
    Path(out.name).replace(SNAPSHOT)


if __name__ == "__main__":
    refresh()
