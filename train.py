"""Treina e avalia os dois modelos. Execute com python train.py."""
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
COLORS = ["#aa4439", "#17695d"]


def plot_data(df):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.facecolor": "white"})
    counts = df["voto"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
    bars = ax.barh(list(LABELS.values()), counts, color=COLORS, height=.48)
    ax.bar_label(bars, padding=5)
    ax.set(xlabel="Avaliações após a limpeza", title="Quantos jogadores recomendaram?", xlim=(0, max(counts) * 1.13))
    fig.savefig(CHARTS / "votos.png", dpi=155)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.5, 3.6), layout="constrained")
    groups = [df.loc[df.voto == k, "palavras"] for k in LABELS]
    bins = np.geomspace(max(1, df.palavras.min()), df.palavras.max() + 1, 25)
    for group, color, label in zip(groups, COLORS, LABELS.values()):
        ax.hist(group, bins=bins, histtype="step", linewidth=2, label=label, color=color)
    ax.set_xscale("log")
    ax.set(xlabel="Palavras por avaliação (escala logarítmica)", ylabel="Avaliações", title="Quanto os jogadores escreveram?")
    ax.legend(frameon=False)
    fig.savefig(CHARTS / "tamanho.png", dpi=155)
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
