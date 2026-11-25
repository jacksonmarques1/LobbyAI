import json
from datetime import datetime, timedelta, timezone
from html import escape
from random import Random, choice
from urllib.parse import quote, urlencode

import streamlit as st

from catalogo import ROOT, SNAPSHOT, refresh
from threading import Lock

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
    return f"app/static/art/{file}" if (ROOT / "static/art" / file).is_file() else escape(g["cover"], quote=True)


def votes(g):
    r = g.get("reviews", {})
    total = r.get("positive", 0) + r.get("negative", 0)
    return (round(r["positive"] * 100 / total), total) if total else (None, 0)


def feedback(g):
    pct, _ = votes(g)
    return f"{pct}% positivas" if pct is not None else "Avaliações indisponíveis"


def nav():
    entries = [("descobrir", "Descobrir"), ("ranking", "Ranking"), ("laboratorio", "Laboratório")]
    active = "descobrir" if page in {"jogo", "catalogo"} else page
    tabs = "".join(f'<a href="{link(pagina=k)}" target="_self" aria-current="{("page" if active == k else "false")}">{label}</a>' for k, label in entries)
    st.html(f'<div class="lobby"><header class="top"><a class="brand" href="?pagina=descobrir" target="_self" aria-label="LobbyAI, início"><i aria-hidden="true">▰</i>LOBBY<span>AI</span></a><nav aria-label="Principal">{tabs}</nav></header></div>')


def hero(g, detail=False):
    title = escape(g["title"])
    url = f'https://store.steampowered.com/app/{g["id"]}/' if detail else link(pagina="jogo", id=g["id"])
    kicker = "FICHA DO JOGO" if detail else "DESTAQUE DA CURADORIA"
    label, target = ("Abrir na Steam", "_blank") if detail else ("Conhecer o jogo", "_self")
    demo = ""
    if detail and g.get("demos"):
        demo_url = f'https://store.steampowered.com/app/{g["demos"][0]}/'
        demo = f'<a class="democta" href="{demo_url}" target="_blank" rel="noopener">Abrir demo na Steam ↗</a>'
    if detail and g.get("free"):
        label = "Jogar grátis na Steam"
    return f'''<section class="feature" style="--art:url('{art(g,"hero")}')">
    <div class="feature-inner"><div class="kicker"><b></b>{kicker}</div><h1>{title}</h1>
    <div class="tags">{escape(g["genre"])} <i> / </i> {escape(g["mode"])}</div>
    <p>{escape(g["summary"])}</p><a class="cta" href="{url}" target="{target}" rel="noopener">{label} <span aria-hidden="true">↗</span></a>{demo}</div></section>'''


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


COLLECTIONS = {
    "Indie": ("Achados indie", "indie"),
    "Demo": ("Demos para testar", "demos"),
    "Grátis": ("Jogos completos grátis", "free"),
    "Cooperativo": ("Pra jogar em companhia", "coop"),
}
FILTERS = {"Indie": "indie", "Demo": "demos", "Grátis": "free", "Cooperativo": "coop",
           "Demos do radar": "from_feed", "Co-op local": "local_coop", "Co-op online": "online_coop", "Solo": "solo"}


def access(g):
    if g.get("free"):
        return "Grátis"
    if g.get("demos"):
        return "Demo disponível"
    return ""


def game_card(g):
    badge = f'<span class="access">{access(g)}</span>' if access(g) else ""
    return f'''<a class="gamecard" href="{link(pagina="jogo",id=g["id"])}" target="_self">
    <div class="jacket"><img src="{art(g,"cover")}" alt="">{badge}</div>
    <div class="card-meta">{escape(g["genre"])} · {escape(g["mode"])}</div>
    <h3>{escape(g["title"])}</h3><p class="reason">{escape(g["summary"])}</p>
    <div class="verdict">{feedback(g)}</div></a>'''


def selection(tag):
    return link(pagina="catalogo", filtro=tag)


def filters_url(selected):
    return link(pagina="catalogo", filtro="|".join(f for f in [*FILTERS, "Fora do radar"] if f in selected))


def catalogue():
    selected = set(st.query_params.get("filtro", "").split("|")) & (set(FILTERS) | {"Fora do radar"})
    pool = [g for g in games if all(g.get(FILTERS[f]) for f in selected if f in FILTERS)]
    if "Fora do radar" in selected:
        measured = sorted((g for g in games if votes(g)[1] and g.get("players")), key=lambda g: g["players"]["count"])
        quiet = {g["id"] for g in measured[:(len(measured)+1)//2]}
        pool = sorted((g for g in pool if g["id"] in quiet), key=lambda g: -votes(g)[0])
    chips = "".join(f'<a class="filter" aria-current="{str(f in selected).lower()}" href="{filters_url(selected ^ {f})}" target="_self">{escape(f)}</a>' for f in [*FILTERS, "Fora do radar"])
    name = next(iter(selected)) if len(selected) == 1 else ""
    heading = COLLECTIONS[name][0] if name in COLLECTIONS else "Explorar o catálogo"
    clear = '<a class="resetlink" href="?pagina=catalogo" target="_self">Limpar filtros</a>' if selected else ""
    jump = f'<a class="textlink" href="{link(pagina="jogo",id=choice(pool)["id"])}" target="_self">Surpreenda-me ↗</a>' if pool else ""
    cards = "".join(game_card(g) for g in pool)
    empty = "" if pool else "<p>Nenhum jogo nesta combinação. Remova um filtro para ver mais opções.</p>"
    st.html(f'''<section class="lobby shelf" id="catalogo"><div class="kicker">CATÁLOGO</div><div class="shelfbar"><h1>{heading}</h1>{jump}</div>
    <div class="filters">{chips}</div><div class="results-count">{len(pool)} {'jogo' if len(pool)==1 else 'jogos'} {clear}</div>
    {empty}<div class="cards">{cards}</div></section>''')


@st.cache_resource
def collection_lock():
    return Lock()


def update_button():
    if st.button("Atualizar catálogo da Steam", help="Consulta as demos e atualiza os indicadores dos jogos. Pode levar alguns minutos."):
        lock = collection_lock()
        if not lock.acquire(blocking=False):
            st.info("Uma atualização já está em andamento. Reabra o catálogo em instantes.")
            return
        try:
            with st.spinner("Consultando demos, avaliações e jogadores na Steam…"):
                refresh()
        except (OSError, ValueError, RuntimeError) as exc:
            st.warning(f"Não foi possível atualizar o catálogo: {exc}")
            return
        finally:
            lock.release()
        st.rerun()


def discover():
    if st.query_params.get("filtro") or page == "catalogo":
        catalogue()
        update_button()
        return
    groups = {tag: [g for g in games if g.get(field)] for tag, (_, field) in COLLECTIONS.items()}
    featured = next((g for g in games if g["id"] == 1607680), games[0])
    links = "".join(f'<a class="collection-link" href="{selection(tag)}" target="_self"><span>{label}</span><small>{len(groups[tag])} jogos</small><b>↗</b></a>' for tag, (label, _) in COLLECTIONS.items())
    st.html(f'''<div class="lobby mast">{hero(featured)}<section class="ranking directory">
    <div class="kicker"><b></b>DESCOBERTA</div><h2>O que jogar?</h2>{links}
    <a class="textlink" href="?pagina=catalogo" target="_self">Explorar os {len(games)} jogos →</a></section></div>''')
    # O recorte inicial de cada coleção muda a cada dia. A coleção completa é estável.
    used = {featured["id"]}
    day = datetime.now(timezone(timedelta(hours=-4))).date().toordinal()
    latest = [g for g in games if g.get("from_feed")]
    if latest:
        stamp = local_time(max(g["store_checked"] for g in latest if g.get("store_checked")))
        st.html(f'<section class="lobby shelf"><div class="kicker">LISTAGEM DA STEAM · {stamp} (MANAUS)</div><div class="shelfbar"><h2>No radar das demos</h2><a class="textlink" href="{selection("Demos do radar")}" target="_self">Ver a seleção ({len(latest)}) →</a></div><div class="cards">' + "".join(game_card(g) for g in latest[:4]) + '</div></section>')
        used.update(g["id"] for g in latest[:4])
    for tag in ("Demo", "Grátis", "Cooperativo", "Indie"):
        group = list(groups[tag])
        if not group:
            continue
        Random(f"{day}:{tag}").shuffle(group)
        group.sort(key=lambda g: g["id"] in used)
        front = group[:4]
        used.update(g["id"] for g in front)
        cards = "".join(game_card(g) for g in front)
        st.html(f'''<section class="lobby shelf"><div class="shelfbar"><h2>{COLLECTIONS[tag][0]}</h2>
        <a class="textlink" href="{selection(tag)}" target="_self">Ver todos ({len(group)}) →</a></div><div class="cards">{cards}</div></section>''')

    update_button()


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
    modes = [label for flag, label in [("local_coop", "Cooperativo local"), ("online_coop", "Cooperativo online"), ("solo", "Solo")] if game.get(flag)]
    if modes:
        st.caption("Modos do jogo completo na Steam · " + " / ".join(modes))
    if game.get("demos"):
        st.caption("A demo pode oferecer apenas parte dos modos do jogo completo.")
    similar = sorted((g for g in games if g["id"] != game["id"]), key=lambda g: (
        g["genre"] == game["genre"], bool(g.get("coop")) == bool(game.get("coop")),
        bool(g.get("free")) == bool(game.get("free")), bool(g.get("demos")) == bool(game.get("demos"))), reverse=True)[:4]
    st.html('<section class="lobby shelf"><div class="shelfbar"><h2>Continue explorando</h2></div><div class="cards">' + "".join(game_card(g) for g in similar) + '</div></section>')
else:
    discover()
