"""
Dashboard de Leads B2B — Demo Comercial
Fase 5.3: Visualización para reuniones de ventas con PYMEs
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Configuración de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Lead Intelligence · B2B Automation",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estilos ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a3d);
        border-radius: 12px;
        padding: 20px 24px;
        border: 1px solid rgba(255,255,255,0.07);
    }
    .score-high    { color: #4cde78; font-weight: 700; }
    .score-medium  { color: #f5c842; font-weight: 700; }
    .score-low     { color: #f5924e; font-weight: 700; }
    .score-discard { color: #888;    font-weight: 700; }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Paleta de colores por score ───────────────────────────────────────────────

SCORE_COLORS = {
    "high":    "#4cde78",
    "medium":  "#f5c842",
    "low":     "#f5924e",
    "discard": "#555b6e",
}

SCORE_LABELS = {
    "high":    "🟢 HIGH",
    "medium":  "🟡 MEDIUM",
    "low":     "🟠 LOW",
    "discard": "⚫ DISCARD",
}


# ── Carga de datos ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    # 1. Datos en vivo (ejecución local con pipeline activo)
    output_dir = Path("data/output")
    csvs = sorted(output_dir.glob("leads_*.csv"), reverse=True)
    # 2. Fallback: datos de demo para Streamlit Cloud
    if not csvs:
        sample = Path("data/sample/leads_sample.csv")
        if sample.exists():
            csvs = [sample]
    if not csvs:
        return pd.DataFrame()
    df = pd.read_csv(csvs[0])
    df["lead_score"] = df["lead_score"].str.lower().str.strip()
    df["company"]    = df["company"].str.title()
    df["location"]   = df["location"].str.strip()
    return df


# ── Sidebar — filtros ─────────────────────────────────────────────────────────

def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/target.png", width=60)
        st.title("Lead Intelligence")
        st.caption("Motor de automatización B2B")
        st.divider()

        st.markdown("### Filtros")

        scores = st.multiselect(
            "Lead Score",
            options=["high", "medium", "low", "discard"],
            default=["high", "medium"],
            format_func=lambda x: SCORE_LABELS.get(x, x),
        )

        sectors = sorted(df["company_sector"].dropna().unique().tolist())
        selected_sectors = st.multiselect(
            "Sector",
            options=sectors,
            default=[],
            placeholder="Todos los sectores",
        )

        sizes = sorted(df["company_size"].dropna().unique().tolist())
        selected_sizes = st.multiselect(
            "Tamaño empresa",
            options=sizes,
            default=[],
            placeholder="Todos los tamaños",
        )

        urgency_filter = st.checkbox("Solo urgentes (incorporación inmediata)", value=False)

        st.divider()
        st.caption(f"Fuente: Indeed.es · {pd.Timestamp.now().strftime('%d/%m/%Y')}")

    # Aplicar filtros
    filtered = df[df["lead_score"].isin(scores)] if scores else df
    if selected_sectors:
        filtered = filtered[filtered["company_sector"].isin(selected_sectors)]
    if selected_sizes:
        filtered = filtered[filtered["company_size"].isin(selected_sizes)]
    if urgency_filter:
        filtered = filtered[filtered["urgency"] == "urgent"]

    return filtered


# ── KPI Cards ─────────────────────────────────────────────────────────────────

def render_kpis(df: pd.DataFrame, filtered: pd.DataFrame) -> None:
    total   = len(filtered)
    high    = len(filtered[filtered["lead_score"] == "high"])
    medium  = len(filtered[filtered["lead_score"] == "medium"])
    rate    = round((high + medium) / len(df) * 100, 1) if len(df) else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total leads analizados", len(df))
    with c2:
        st.metric("🟢 Leads HIGH", high, delta=f"{round(high/len(df)*100)}% del total" if len(df) else None)
    with c3:
        st.metric("🟡 Leads MEDIUM", medium)
    with c4:
        st.metric("Tasa de conversión", f"{rate}%", help="(HIGH + MEDIUM) / total analizado")


# ── Gráficos ──────────────────────────────────────────────────────────────────

def render_charts(filtered: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">Distribución por Score</p>', unsafe_allow_html=True)
        score_counts = filtered["lead_score"].value_counts().reset_index()
        score_counts.columns = ["score", "count"]
        score_counts["label"] = score_counts["score"].map(SCORE_LABELS)
        fig = px.pie(
            score_counts, values="count", names="label",
            color="score",
            color_discrete_map={k: SCORE_COLORS[k] for k in SCORE_COLORS},
            hole=0.55,
        )
        fig.update_traces(textposition="outside", textinfo="label+percent")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(t=10, b=10),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">Leads HIGH por Sector</p>', unsafe_allow_html=True)
        sector_df = (
            filtered[filtered["lead_score"] == "high"]
            .groupby("company_sector")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
        )
        if sector_df.empty:
            st.info("Sin leads HIGH en la selección actual.")
        else:
            fig2 = px.bar(
                sector_df, x="count", y="company_sector",
                orientation="h",
                color_discrete_sequence=["#4cde78"],
                labels={"company_sector": "", "count": "Leads HIGH"},
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                margin=dict(t=10, b=10),
                height=280,
            )
            st.plotly_chart(fig2, use_container_width=True)


# ── Tabla de leads ────────────────────────────────────────────────────────────

def render_table(filtered: pd.DataFrame) -> None:
    st.markdown('<p class="section-title">Listado de Leads</p>', unsafe_allow_html=True)

    display_cols = [
        "lead_score", "company", "title", "location",
        "company_sector", "urgency", "lead_reason", "url",
    ]
    cols = [c for c in display_cols if c in filtered.columns]
    display_df = filtered[cols].copy()
    display_df["lead_score"] = display_df["lead_score"].map(SCORE_LABELS).fillna(display_df["lead_score"])

    # Ordenar HIGH primero
    order = {"🟢 HIGH": 0, "🟡 MEDIUM": 1, "🟠 LOW": 2, "⚫ DISCARD": 3}
    display_df["_sort"] = display_df["lead_score"].map(order).fillna(4)
    display_df = display_df.sort_values("_sort").drop(columns=["_sort"])

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "url": st.column_config.LinkColumn("Oferta", display_text="Ver →"),
            "lead_score": st.column_config.TextColumn("Score", width="small"),
            "company": st.column_config.TextColumn("Empresa", width="medium"),
            "title": st.column_config.TextColumn("Puesto", width="large"),
            "lead_reason": st.column_config.TextColumn("Razón IA", width="large"),
        },
    )


# ── Exportar selección ────────────────────────────────────────────────────────

def render_export(filtered: pd.DataFrame) -> None:
    col1, col2 = st.columns([3, 1])
    with col2:
        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Exportar selección CSV",
            data=csv_bytes,
            file_name=f"leads_seleccion_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ── App principal ─────────────────────────────────────────────────────────────

def main() -> None:
    df = load_data()

    if df.empty:
        st.error("No hay datos en data/output/. Ejecuta primero el pipeline.")
        st.code("PYTHONPATH=src python src/main.py --skip-enrich\nPYTHONPATH=src python src/cleaner/lead_enricher.py")
        st.stop()

    filtered = render_sidebar(df)

    # Header
    st.markdown("## 🎯 Lead Intelligence Dashboard")
    st.caption("Empresas detectando trabajo manual → candidatos ideales para automatización de backoffice")
    st.divider()

    render_kpis(df, filtered)
    st.divider()
    render_charts(filtered)
    st.divider()
    render_table(filtered)
    render_export(filtered)

    # Footer
    st.markdown(
        "<br><center><small>Powered by Claude Haiku · Indeed.es · "
        "Pipeline Scraping + IA</small></center>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
