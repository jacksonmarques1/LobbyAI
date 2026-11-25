import json
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote, urlencode

import streamlit as st

from catalogo import ROOT, SNAPSHOT

st.set_page_config(page_title="LobbyAI — Descobrir jogos", page_icon="🕹️", layout="wide")
st.html("<style>" + (ROOT / "interface.css").read_text("utf-8") + "</style>")
games = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
by_id = {str(g["id"]): g for g in games}
ranked = sorted((g for g in games if g.get("players")), key=lambda g: -g["players"]["count"])
page = st.query_params.get("pagina", "descobrir")


def link(**query):
    return "?" + escape(urlencode(query), quote=True)


def local_time(value):
    return datetime.fromisoformat(value).astimezone(timezone(timedelta(hours=-4))).strftime("%d/%m · %Hh%M")


def fmt(value):
    return f"{value:,}".replace(",", ".")


def art(g, kind):
    file = f"{g['id']}-{kind}.webp"
    return f"app/static/art/{file}" if (ROOT / "static/art" / file).is_file() else escape(g[kind], quote=True)


def votes(g):
    r = g.get("reviews", {})
    total = r.get("positive", 0) + r.get("negative", 0)
    return (round(r["positive"] * 100 / total), total) if total else (None, 0)


def feedback(g):
    pct, _ = votes(g)
    return f"{pct}% positivas" if pct is not None else "Avaliações indisponíveis"


def nav():
    entries = [("descobrir", "Descobrir"), ("ranking", "Ranking"), ("laboratorio", "Laboratório")]
    active = "descobrir" if page == "jogo" else page
    tabs = "".join(f'<a href="{link(pagina=k)}" target="_self" aria-current="{("page" if active == k else "false")}">{label}</a>' for k, label in entries)
    st.html(f'<div class="lobby"><header class="top"><a class="brand" href="?pagina=descobrir" target="_self" aria-label="LobbyAI, início"><i aria-hidden="true">▰</i>LOBBY<span>AI</span></a><nav aria-label="Principal">{tabs}</nav></header></div>')


def hero(g, detail=False):
    title = escape(g["title"])
    url = f'https://store.steampowered.com/app/{g["id"]}/' if detail else link(pagina="jogo", id=g["id"])
    kicker = "FICHA DO JOGO" if detail else "DESTAQUE DA CURADORIA"
    label, target = ("Abrir na Steam", "_blank") if detail else ("Conhecer o jogo", "_self")
    return f'''<section class="feature" style="--art:url('{art(g,"hero")}')">
    <div class="feature-inner"><div class="kicker"><b></b>{kicker}</div><h1>{title}</h1>
    <div class="tags">{escape(g["genre"])} <i> / </i> {escape(g["mode"])}</div>
    <p>{escape(g["summary"])}</p><a class="cta" href="{url}" target="{target}" rel="noopener">{label} <span aria-hidden="true">↗</span></a></div></section>'''


def rankings(full=False):
    rows = []
    for i, g in enumerate(ranked if full else ranked[:4], 1):
        rows.append(f'''<a class="rankrow" href="{link(pagina="jogo",id=g["id"])}" target="_self">
        <span class="position">{i:02}</span><img alt="" src="{art(g,"cover")}"><div class="rankname">{escape(g["title"])}<small>{escape(g["genre"])}</small></div>
        <strong>{fmt(g["players"]["count"])}</strong></a>''')
    stamp = local_time(max(g["players"]["consultado"] for g in ranked)) if ranked else "indisponível"
    more = '' if full else '<a class="textlink" href="?pagina=ranking" target="_self">Ranking completo <span>→</span></a>'
    return f'''<section class="ranking"><div class="kicker"><b></b>JOGADORES SIMULTÂNEOS</div><h2>Mais jogados</h2>
    <div>{"".join(rows) or "Dados indisponíveis."}</div>{more}<small class="stamp">Steam · {stamp} (Manaus) · {len(games)} jogos no catálogo</small></section>'''


def game_card(g):
    mark = "<b>+</b>" if votes(g)[1] else ""
    return f'''<a class="gamecard" href="{link(pagina="jogo",id=g["id"])}" target="_self">
    <img src="{art(g,"cover")}" alt=""><div class="card-meta">{escape(g["genre"])} <span> / </span> {escape(g["mode"])}</div>
    <h3>{escape(g["title"])}</h3><div class="verdict">{mark} {feedback(g)}</div></a>'''


def discover():
    st.html(f'<div class="lobby mast">{hero(games[0])}{rankings()}</div>')
    modes = ["Todos", "Solo", "Cooperativo", "Fora do radar"]
    selected = st.query_params.get("filtro", "Todos")
    if selected not in modes:
        selected = "Todos"
    filters = "".join(f'<a class="filter" aria-current="{("true" if m == selected else "false")}" href="{link(filtro=m)}#catalogo" target="_self">{m}</a>' for m in modes)
    items = games[1:] + games[:1]
    note = ""
    if selected == "Fora do radar":
        items = sorted((g for g in games if votes(g)[0] is not None and g.get("players")),
                       key=lambda g: g["players"]["count"])[:len(games)//2]
        items.sort(key=lambda g: -votes(g)[0])
        note = "<p>Entre os jogos com menos jogadores no catálogo, estes receberam mais avaliações positivas em proporção.</p>"
    elif selected != "Todos":
        items = [g for g in items if g["mode"] == selected]
    cards = "".join(game_card(g) for g in items)
    st.html(f'<section class="lobby shelf" id="catalogo"><div class="shelfbar"><h2>Descobrir jogos</h2><div class="filters" aria-label="Filtrar jogos">{filters}</div></div>{note}<div class="cards">{cards}</div></section>')


nav()
if page == "laboratorio":
    st.html('<div class="lobby section-title"><div class="kicker">MACHINE LEARNING</div><h1>Laboratório de avaliações</h1><p>O modelo tenta prever o voto de quem escreveu uma avaliação em português.</p></div>')
    from review_lab import render
    render()
elif page == "ranking":
    st.html(f'<div class="lobby rankfull">{rankings(full=True)}<p>Ordem pela última contagem disponível na Steam. Consulte o horário de cada leitura na ficha do jogo.</p></div>')
elif page == "jogo" and st.query_params.get("id") in by_id:
    game = by_id[st.query_params["id"]]
    pct, total = votes(game)
    r, p = game.get("reviews"), game.get("players")
    streams = "https://www.twitch.tv/search?term=" + quote(game["title"])
    reviews = f"{fmt(total)} votos acumulados · SteamSpy · {local_time(r['consultado'])} (Manaus)" if total else "Sem leitura disponível"
    players = f"Steam · {local_time(p['consultado'])} (Manaus)" if p else "Sem leitura disponível"
    st.html(f'''<div class="lobby detail">{hero(game, detail=True)}<div class="detailgrid">
    <section><h2>Voto da comunidade</h2><strong>{feedback(game)}</strong><small>{reviews}</small></section>
    <section><h2>Jogadores simultâneos</h2><strong>{fmt(p["count"]) if p else "—"}</strong><small>{players}</small></section>
    <section><h2>Transmissões</h2><a class="textlink" href="{streams}" target="_blank" rel="noopener">Buscar na Twitch ↗</a><small>Consulte os canais na Twitch.</small></section></div></div>''')
else:
    discover()
