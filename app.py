import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data_prep import load_and_prepare, kpi_overview
from chatbot import answer

st.set_page_config(page_title="Datlas Sales Intelligence Tool", layout="centered")
st.title("Datlas – Sales Intelligence Tool (Dashboard + Chatbot)")

@st.cache_data
def get_df():
    return load_and_prepare()

with st.sidebar:
    uploaded_file = st.file_uploader("Carica dati CSV/XLSX", type=["csv", "xlsx"])

if uploaded_file is not None:
    df = load_and_prepare(uploaded_file)
    st.sidebar.success(f"Caricato: {uploaded_file.name}")
else:
    df = get_df()
    st.sidebar.info("Caricando dataset locale da `data/`. Se non c'è un file, usa il sample oppure caricane uno.")

if df.empty:
    st.sidebar.warning(
        "Nessun file di dati trovato. Carica un CSV/XLSX nella sidebar o aggiungi il file nella cartella `data/`."
    )
    st.warning(
        "Nessun dato disponibile al momento. Assicurati di avere un file CSV/XLSX in `data/` oppure caricalo nella sidebar."
    )
    st.stop()

# ==============================
# SIDEBAR FILTERS (SAFE)
# ==============================
st.sidebar.header("Filtri")

settori_lista = sorted(df["settore_codice"].dropna().astype(str).unique().tolist())
lobs_lista = sorted(df["LOB"].dropna().astype(str).unique().tolist())
teams_lista = sorted(df["team"].dropna().astype(str).unique().tolist())
servizi_lista = sorted(df["Servizi A&M"].dropna().astype(str).unique().tolist())
stati_lista = sorted(df["stato"].dropna().astype(str).unique().tolist())

settori = st.sidebar.multiselect("Industry (settore_codice)", settori_lista)
lobs = st.sidebar.multiselect("LOB", lobs_lista)
teams = st.sidebar.multiselect("Team", teams_lista)
servizi = st.sidebar.multiselect("Servizi A&M", servizi_lista)
stati = st.sidebar.multiselect("Stato", stati_lista, default=stati_lista)

# ==============================
# APPLY FILTERS
# ==============================
fdf = df.copy()

if settori:
    fdf = fdf[fdf["settore_codice"].astype(str).isin(settori)]
if lobs:
    fdf = fdf[fdf["LOB"].astype(str).isin(lobs)]
if teams:
    fdf = fdf[fdf["team"].astype(str).isin(teams)]
if servizi:
    fdf = fdf[fdf["Servizi A&M"].astype(str).isin(servizi)]
if stati:
    fdf = fdf[fdf["stato"].astype(str).isin(stati)]

# ==============================
# KPI ROW
# ==============================
kpi = kpi_overview(fdf)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Venduto 2026", f"{kpi['venduto_2026']:,.0f} €")
c2.metric("Venduto 2025", f"{kpi['venduto_2025']:,.0f} €")
c3.metric("Pipeline Lorda 2026 (attiva)", f"{kpi['pipeline_lorda_2026']:,.0f} €")
c4.metric("Pipeline Pesata 2026 (attiva)", f"{kpi['pipeline_pesata_2026']:,.0f} €")
c5.metric("Conversione (Venduta su chiuse)", f"{kpi['conversion_rate_closed']*100:.1f}%")
c6.metric("Qualità pipeline (Persa+Eliminata)", f"{kpi['lost_rate_closed']*100:.1f}%")

st.divider()

TAB1, TAB2, TAB3, TAB4, TAB5 = st.tabs(
    ["Executive", "Mix", "Concentrazione", "Cross-selling", "Chatbot"]
)

# ==============================
# TAB 1 – EXECUTIVE
# ==============================
with TAB1:
    st.subheader("Executive Overview")

    stage = (
        fdf.groupby("stato", as_index=False)
        .agg(
            n=("stato", "count"),
            ricavo_2026=("ricavo_2026", "sum"),
            pipeline_pesata_2026=("pipeline_pesata_2026", "sum"),
        )
    )

    st.plotly_chart(
        px.bar(stage.sort_values("n", ascending=False), x="stato", y="n",
               title="Distribuzione opportunità per stato (include Persa/Eliminata)"),
        use_container_width=True,
    )

    st.plotly_chart(
        px.bar(stage, x="stato", y="pipeline_pesata_2026",
               title="Pipeline pesata 2026 (solo stati attivi)"),
        use_container_width=True,
    )

# ==============================
# TAB 2 – MIX
# ==============================
with TAB2:
    st.subheader("Mix di Business")

    sold = fdf[fdf["is_venduto"]]
    if sold.empty:
        st.warning("Nessun dato venduto nel perimetro filtrato.")
    else:
        pivot = sold.pivot_table(
            values="ricavo_2026",
            index="settore_codice",
            columns="LOB",
            aggfunc="sum",
            fill_value=0
        )
        st.plotly_chart(
            px.imshow(pivot, aspect="auto", title="Fatturato 2026 (venduto) – Industry x LOB"),
            use_container_width=True
        )

        svc = (
            sold.groupby("Servizi A&M", as_index=False)["ricavo_2026"]
            .sum()
            .sort_values("ricavo_2026", ascending=False)
            .head(15)
        )
        fig = px.bar(svc, x="Servizi A&M", y="ricavo_2026",
                     title="Top 15 servizi per fatturato 2026 (venduto)")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# ==============================
# TAB 3 – CONCENTRAZIONE
# ==============================
with TAB3:
    st.subheader("Concentrazione & Dipendenza")

    sold_client = (
        fdf[fdf["is_venduto"]]
        .groupby("cliente_codice", as_index=False)["ricavo_2026"]
        .sum()
        .sort_values("ricavo_2026", ascending=False)
    )

    if sold_client.empty:
        st.warning("Nessun dato venduto nel perimetro filtrato.")
    else:
        top10 = sold_client.head(10)
        share = top10["ricavo_2026"].sum() / sold_client["ricavo_2026"].sum()

        st.info(f"Top 10 clienti = ~{share:.1%} del venduto 2026 nel perimetro filtrato.")
        st.plotly_chart(
            px.bar(top10, x="cliente_codice", y="ricavo_2026",
                   title="Top 10 clienti per venduto 2026"),
            use_container_width=True
        )

# ==============================
# TAB 4 – CROSS-SELLING
# ==============================
with TAB4:
    st.subheader("Cross-selling & Sviluppo")

    sold = fdf[fdf["is_venduto"]]
    if sold.empty:
        st.warning("Nessun dato venduto nel perimetro filtrato.")
    else:
        svc_count = (
            sold.groupby("cliente_codice")["Servizi A&M"]
            .nunique()
            .reset_index()
            .rename(columns={"Servizi A&M": "n_servizi"})
        )

        mono = int((svc_count["n_servizi"] == 1).sum())
        multi = int((svc_count["n_servizi"] > 1).sum())

        st.plotly_chart(
            px.pie(
                values=[mono, multi],
                names=["Mono-servizio", "Multi-servizio"],
                title="Clienti venduti: mono vs multi-servizio",
            ),
            use_container_width=True
        )

        rev = sold.groupby("cliente_codice", as_index=False)["ricavo_2026"].sum()
        cand = svc_count.merge(rev, on="cliente_codice")
        med = cand["ricavo_2026"].median() if len(cand) else 0

        cand = (
            cand[(cand["n_servizi"] == 1) & (cand["ricavo_2026"] >= med)]
            .sort_values("ricavo_2026", ascending=False)
            .head(25)
        )

        st.write("Candidati cross-selling (euristica): mono-servizio + ricavo ≥ mediana")
        st.dataframe(cand, use_container_width=True)

# ==============================
# TAB 5 – CHATBOT
# ==============================
with TAB5:
    st.subheader("Chatbot")
    q = st.text_input("Fai una domanda")
    if st.button("Rispondi") and q:
        res = answer(q, fdf)
        st.write(res["text"])

        if "table" in res:
            st.dataframe(res["table"], use_container_width=True)

        if "chart" in res:
            kind, tab, x, y = res["chart"]
            if kind == "bar":
                st.plotly_chart(px.bar(tab, x=x, y=y), use_container_width=True)
            elif kind == "pie":
                st.plotly_chart(px.pie(tab, names=x, values=y), use_container_width=True)
            elif kind == "bar_group":
                fig = go.Figure()
                for col in y:
                    fig.add_bar(name=col, x=tab[x], y=tab[col])
                fig.update_layout(barmode="group")
                st.plotly_chart(fig, use_container_width=True)
