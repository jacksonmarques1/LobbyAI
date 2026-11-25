"""Treina e avalia os dois modelos. Execute com python train.py."""
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from corpus import LABELS, ROOT, load_reviews

SEED = 42
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "graficos"
MODEL = ROOT / "models" / "lobbyai.joblib"
NIGHT = "#101211"
PAPER = "#f3f3eb"
MUTED = "#b5bab0"
RULE = "#393d38"
VOTE_COLORS = {1: "#d9ff58", 0: "#b4a6ef"}
DISPLAY = ROOT / "static/fonts/BarlowCondensed-BoldItalic.ttf"
NARROW = ROOT / "static/fonts/BarlowCondensed-SemiBold.ttf"


def chart(title, height):
    fig = plt.figure(figsize=(8, height), facecolor=NIGHT)
    fig.text(.055, 1 - .22 / height, title, va="top", color=PAPER,
             fontproperties=FontProperties(fname=DISPLAY, size=27))
    return fig


def plot_data(df):
    counts = df["voto"].value_counts().reindex(VOTE_COLORS, fill_value=0)
    total = len(df)
    fig = chart("Como os jogadores votaram?", 2.65)
    total_label = f"{total:,}".replace(",", ".")
    fig.text(.055, .67, f"{total_label} avaliações em português na amostra", color=MUTED, fontsize=13)
    band = fig.add_axes([.055, .48, .89, .09])
    band.set(xlim=(0, total), ylim=(0, 1))
    band.set_axis_off()
    offset = 0
    for vote, count in counts.items():
        band.barh(.5, count, left=offset, height=1, color=VOTE_COLORS[vote],
                  edgecolor=NIGHT, linewidth=1)
        offset += count
    for x, vote in zip([.055, .52], counts.index):
        count = counts[vote]
        number = f"{count:,}".replace(",", ".")
        share = f"{100 * count / total:g}".replace(".", ",")
        fig.text(x, .29, LABELS[vote], color=VOTE_COLORS[vote], fontsize=14)
        fig.text(x, .105, f"{number}  ·  {share}%", color=PAPER,
                 fontproperties=FontProperties(fname=NARROW, size=27))
    fig.savefig(CHARTS / "votos.png", dpi=175)
    plt.close(fig)

    fig = chart("Quanto os jogadores escreveram?", 4.2)
    fig.text(.055, .80, "Avaliações por faixa de palavras", color=MUTED, fontsize=13)
    ax = fig.add_axes([.07, .16, .88, .49], facecolor=NIGHT)
    bins = [0, 250, 500, 750, np.inf]
    centers = np.arange(len(bins) - 1)
    for vote, shift in zip(VOTE_COLORS, [-.19, .19]):
        words = df.loc[df.voto == vote, "palavras"]
        values, _ = np.histogram(words, bins=bins)
        bars = ax.bar(centers + shift, values, width=.32, color=VOTE_COLORS[vote], label=LABELS[vote])
        ax.bar_label(bars, padding=3, color=PAPER, fontsize=12)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.03), ncols=2, frameon=False,
              labelcolor=PAPER, fontsize=12, handlelength=1, borderaxespad=0)
    ax.set_xticks(centers, ["Até 249", "250 a 499", "500 a 749", "750 ou mais"])
    ax.tick_params(axis="x", colors=PAPER, labelsize=12, length=0, pad=8)
    ax.set_yticks([])
    ax.set_ylim(0, ax.dataLim.ymax * 1.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    fig.savefig(CHARTS / "tamanho.png", dpi=175)
    plt.close(fig)


def main():
    CHARTS.mkdir(parents=True, exist_ok=True)
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    raw = load_reviews()
    valid = raw.texto.str.contains(r"[^\W\d_]", regex=True)
    df = raw.loc[valid].copy()
    df["chave"] = df.texto.str.casefold().str.replace(r"[\W_]+", " ", regex=True).str.strip()
    conflict = df.groupby("chave").voto.transform("nunique") > 1
    clean_df = df.loc[~conflict].drop_duplicates("chave").copy()
    clean_df["palavras"] = clean_df.texto.str.split().str.len()
    plot_data(clean_df)
    train, test = train_test_split(clean_df, test_size=.2, random_state=SEED, stratify=clean_df.voto)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    algorithms = {"Naive Bayes": MultinomialNB(), "Regressão Logística": LogisticRegression(max_iter=1000, random_state=SEED)}
    report = {
        "originais": len(raw), "sem_texto": int((~valid).sum()), "conflitantes": int(conflict.sum()),
        "duplicadas": len(df.loc[~conflict]) - len(clean_df), "validas": len(clean_df),
        "treino": len(train), "teste": len(test),
        "quantidades": {LABELS[k]: int((clean_df.voto == k).sum()) for k in LABELS},
        "mediana_palavras": {LABELS[k]: float(clean_df.loc[clean_df.voto == k, "palavras"].median()) for k in LABELS},
        "ate_20_palavras": int((clean_df.palavras <= 20).sum()), "modelos": {}
    }
    pipelines = {}
    for name, algorithm in algorithms.items():
        pipeline = Pipeline([("texto", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                                                      strip_accents="unicode", token_pattern=r"(?u)\b[^\W\d_]{2,}\b")),
                             ("classificador", algorithm)])
        score = cross_val_score(pipeline, train.texto, train.voto, scoring="f1_macro", cv=cv)
        pipelines[name] = pipeline.fit(train.texto, train.voto)
        report["modelos"][name] = {"f1_validacao": float(score.mean())}
    # A escolha é feita antes de avaliar os modelos nas avaliações reservadas.
    best = max(algorithms, key=lambda name: report["modelos"][name]["f1_validacao"])
    report["escolhido"] = best
    for name, pipeline in pipelines.items():
        pred = pipeline.predict(test.texto)
        report["modelos"][name].update({
            "acertos": int((pred == test.voto).sum()), "f1_macro": f1_score(test.voto, pred, average="macro"),
            "metricas": classification_report(test.voto, pred, labels=[0, 1], target_names=list(LABELS.values()),
                                               output_dict=True, zero_division=0),
            "matriz": confusion_matrix(test.voto, pred, labels=[0, 1]).tolist()
        })
    test = test.copy()
    test["previsto"] = pipelines[best].predict(test.texto)
    # Exemplos para discussão, escolhidos depois da avaliação. O arquivo guarda apenas IDs.
    examples = []
    for actual, correct in [(1, True), (0, True), (0, False)]:
        subset = test[(test.voto == actual) & ((test.voto == test.previsto) == correct)]
        if len(subset):
            row = subset.sort_values(["palavras", "id"]).iloc[0]
            examples.append({"id": row.id, "voto": int(row.voto), "previsto": int(row.previsto)})
    report["demonstracao"] = examples
    joblib.dump(pipelines[best], MODEL, compress=3)
    (REPORTS / "metricas.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
