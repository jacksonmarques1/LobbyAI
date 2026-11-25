import json
from urllib.error import URLError

import joblib
import pandas as pd
import streamlit as st

from corpus import LABELS, ROOT, clean, load_reviews

st.set_page_config(page_title="LobbyAI · Avaliações da Steam", page_icon="🎮", layout="centered")
st.markdown("""<style>
.block-container {max-width: 54rem; padding-top: 2.7rem;}
h1 {letter-spacing: -.055em;}
[data-baseweb="tab-list"] {gap: 1rem;}
[data-testid="stForm"] {background: white;}
</style>""", unsafe_allow_html=True)
st.title("LobbyAI")
st.write("Dá pra adivinhar o voto de um jogador só pelo comentário?")


@st.cache_resource
def load_model():
    return joblib.load(ROOT / "models" / "lobbyai.joblib")


@st.cache_data
def demo_reviews():
    return load_reviews().set_index("id").texto


try:
    model = load_model()
    report = json.loads((ROOT / "reports" / "metricas.json").read_text(encoding="utf-8"))
except (OSError, ValueError, EOFError, KeyError, ImportError) as exc:
    st.error("Não foi possível abrir o modelo ou o relatório. Execute python train.py na pasta do projeto.")
    st.stop()

best = report["escolhido"]
score = report["modelos"][best]
tab_review, tab_demo, tab_scores = st.tabs(["Analisar comentário", "Teste às cegas", "Resultados"])


def show_prediction(text):
    prediction = int(model.predict([text])[0])
    st.subheader("Provavelmente recomendou 👍" if prediction else "Provavelmente não recomendou 👎")
    st.caption("Previsão do modelo para o voto de quem escreveu.")


with tab_review:
    with st.form("review"):
        review = st.text_area("O que o jogador escreveu?", height=140,
                              placeholder="Ex.: Terminei a campanha ontem e já comecei outra com meus amigos.")
        submitted = st.form_submit_button("Analisar comentário", type="primary")
    if submitted:
        text = clean(review)
        if not text or not any(letter.isalpha() for letter in text):
            st.warning("Escreva uma avaliação em português antes de analisar.")
        elif model.named_steps["texto"].transform([text]).nnz == 0:
            st.warning("O modelo não reconheceu palavras nesse comentário. Tente descrever sua experiência no jogo.")
        else:
            show_prediction(text)
    st.caption(f"Protótipo educacional · {best} · {score['acertos']} acertos em {report['teste']} avaliações de teste.")

with tab_demo:
    st.subheader("Qual foi o voto?")
    st.write("Leia uma avaliação reservada para o teste, dê seu palpite e revele o voto do jogador.")
    if "show_cases" not in st.session_state:
        st.session_state.show_cases = False
    if not st.session_state.show_cases:
        if st.button("Carregar avaliações", help="Na primeira vez, os textos são baixados da base pública da pesquisa."):
            st.session_state.show_cases = True
            st.rerun()
    if st.session_state.show_cases:
        try:
            reviews = demo_reviews()
        except (OSError, URLError, ValueError):
            st.info("Não foi possível ler a base. Conecte-se à internet na primeira execução ou rode python train.py.")
        else:
            cases = report["demonstracao"]
            selected = st.radio("Avaliação", range(len(cases)), format_func=lambda i: f"Caso {i + 1}", horizontal=True)
            case = cases[selected]
            original = reviews.at[case["id"]]
            st.text(original)
            if st.button("Revelar previsão e voto", key=f"revelar_{selected}"):
                show_prediction(original)
                st.write(f"**Voto real do jogador:** {LABELS[case['voto']]}.")

with tab_scores:
    st.subheader("Como os modelos se saíram")
    st.write(f"O treino usou {report['treino']} avaliações. Outras {report['teste']} ficaram reservadas para o teste.")
    rows = []
    for name, item in report["modelos"].items():
        macro = item["metricas"]["macro avg"]
        rows.append({"Modelo": name, "Acertos": item["acertos"],
                     "Acurácia": f"{item['metricas']['accuracy']:.2%}", "Precisão macro": f"{macro['precision']:.2%}",
                     "Recall macro": f"{macro['recall']:.2%}", "F1 macro": f"{item['f1_macro']:.2%}"})
    st.dataframe(pd.DataFrame(rows).set_index("Modelo"), width="stretch")
    st.write(f"**{best}** teve o maior F1 macro na validação com cinco divisões do treino. Essa medida dá o mesmo peso aos dois votos.")
    st.subheader("Onde o modelo errou")
    matrix = pd.DataFrame(score["matriz"], index=["Voto real 👎", "Voto real 👍"], columns=["Previu 👎", "Previu 👍"])
    st.table(matrix)
    with st.expander("Conhecer a base de treino e teste"):
        st.image(str(ROOT / "reports/graficos/votos.png"))
        st.image(str(ROOT / "reports/graficos/tamanho.png"))
    st.caption("O modelo aprendeu com avaliações em português brasileiro. Frases curtas, gírias e ironia podem mudar o sentido de uma crítica.")
