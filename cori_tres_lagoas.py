import streamlit as st
import pandas as pd
import plotly.express as px
import sqlalchemy as sa
import plotly.graph_objects as go

# ============================
# ⚠️ Segurança: use st.secrets
# Em .streamlit/secrets.toml (ou no painel do Streamlit Cloud):
# [db]
# url = "mysql+pymysql://USUARIO:SENHA@ljsystem.com.br/ljsyst02_Cori_Iot"
# ============================
DB_URL = st.secrets["db"]["url"]  # sem fallback com credenciais no código

# ----------------------------
# Configuração do app
# ----------------------------
st.set_page_config(layout="wide", page_title="Cori Ingredientes - Três Lagoas")
st.title("Cori Ingredientes - Três Lagoas")

@st.cache_data(ttl=300)
def load_data(db_url: str) -> pd.DataFrame:
    engine = sa.create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)
    with engine.begin() as conn:
        df = pd.read_sql("SELECT * FROM tbl_oee_moinho", conn)
    return df

df = load_data(DB_URL).copy()

# ===== Preparação =====
df["data"] = pd.to_datetime(df.get("inicio", pd.NaT), errors="coerce")
df = df.dropna(subset=["data"]).sort_values("data").reset_index(drop=True)
df["year"]  = df["data"].dt.to_period("Y")
df["month"] = df["data"].dt.to_period("M")

# ===== Sidebar =====
st.sidebar.markdown("**Cori 3 Lagoas**")
st.sidebar.divider()

linhas_disponiveis = sorted(df["linha"].dropna().unique().tolist()) if "linha" in df.columns else []
linha = st.sidebar.multiselect(
    "Linha",
    options=linhas_disponiveis,
    default=linhas_disponiveis if linhas_disponiveis else []
)
df_filtro1 = df[df["linha"].isin(linha)] if linha else df.copy()

anos = sorted(df_filtro1["year"].dropna().unique().tolist())
year = st.sidebar.selectbox("Ano", anos, index=len(anos)-1 if anos else 0) if anos else None
df_filtro2 = df_filtro1[df_filtro1["year"] == year] if year is not None else df_filtro1.copy()

meses = sorted(df_filtro2["month"].dropna().unique().tolist())
month = st.sidebar.selectbox("Mês", meses, index=len(meses)-1 if meses else 0) if meses else None
df_filtro3 = df_filtro2[df_filtro2["month"] == month] if month is not None else df_filtro2.copy()

# ===== Helpers =====
def safe_mean(series, default=0.0):
    try:
        val = float(series.dropna().astype(float).mean())
        return 0.0 if pd.isna(val) else val
    except Exception:
        return default

def safe_sum(series, default=0.0):
    try:
        val = float(series.dropna().astype(float).sum())
        return 0.0 if pd.isna(val) else val
    except Exception:
        return default

def fmt_pct(x):
    try:
        return f"{round(float(x))}%"
    except Exception:
        return "0%"

def prep_group(df_):
    if df_.empty:
        return pd.DataFrame({"month": [], "producao_media": [], "producao_total": [], "month_label": []})
    base = df_.copy()
    base["producao"] = pd.to_numeric(base["producao"], errors="coerce")

    g = (
        base
        .groupby("month", as_index=False)
        .agg(
            producao_media=("producao", "mean"),
            producao_total=("producao", "sum"),
        )
    )
    g["month_label"] = g["month"].dt.strftime("%b %Y")
    return g

agg = prep_group(df_filtro1)

total_oee = (
    df_filtro1.groupby("month", as_index=False)["oee"].mean()
    if (not df_filtro1.empty and "oee" in df_filtro1.columns)
    else pd.DataFrame({"month": [], "oee": []})
)
if not total_oee.empty:
    total_oee["month_label"] = total_oee["month"].dt.strftime("%b %Y")

# ===== Abas =====
tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📈 Séries", "📋 Tabela"])

# --------------------------------------------------------------------
# TAB 1 — Visão Geral
# --------------------------------------------------------------------
with tab1:
    # ---- Métricas (médias do mês selecionado) ----
    col1, col2, col3, col4 = st.columns(4)
    oee_val  = safe_mean(df_filtro3.get("oee", pd.Series(dtype=float)))
    perf_val = safe_mean(df_filtro3.get("performance", pd.Series(dtype=float)))
    disp_val = safe_mean(df_filtro3.get("disponibilidade", pd.Series(dtype=float)))
    qual_val = safe_mean(df_filtro3.get("qualidade", pd.Series(dtype=float)))

    with col1: st.metric(label="OEE", value=fmt_pct(oee_val))
    with col2: st.metric(label="PERFORMANCE", value=fmt_pct(perf_val))
    with col3: st.metric(label="DISPONIBILIDADE", value=fmt_pct(disp_val))
    with col4: st.metric(label="QUALIDADE", value=fmt_pct(qual_val))

    # ---- Produção e Rejeito (média do mês) ----
    col5, col6 = st.columns(2)
    with col5:
        st.metric(
            label="PRODUÇÃO (média no mês)",
            value=round(safe_mean(df_filtro3.get("producao", pd.Series(dtype=float))))
        )
    with col6:
        st.metric(
            label="REJEITO (média no mês)",
            value=round(safe_mean(df_filtro3.get("rejeito", pd.Series(dtype=float))))
        )

    # ---- Barras: média diária e total mensal ----
    col7, col8 = st.columns(2)

    with col7:
        if agg.empty:
            st.info("Sem dados para **Média Diária da Produção por Mês**.")
        else:
            fig = px.bar(
                agg,
                x="month_label",
                y="producao_media",
                text=agg["producao_media"].round(0).astype(int),  # exibe como inteiro
                labels={"month_label": "Mês", "producao_media": "Média Diária"},
                title="Média Diária da Produção por Mês"
            )
            fig.update_traces(texttemplate="%{text:d}")
            fig.update_layout(
                yaxis=dict(
                    title="Média Diária",
                    range=[0, max(20000, (agg["producao_media"].max() or 0) * 1.2)]
                ),
                xaxis=dict(title="Mês"),
                uniformtext_minsize=14,
                uniformtext_mode="hide"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col8:
        if agg.empty:
            st.info("Sem dados para **Total Mensal da Produção**.")
        else:
            fig2 = px.bar(
                agg,
                x="month_label",
                y="producao_total",
                text="producao_total",
                labels={"month_label": "Mês", "producao_total": "Total Mensal"},
                title="Total Mensal da Produção"
            )
            y_max = max(300000, (agg["producao_total"].max() or 0) * 1.2)
            fig2.update_layout(
                yaxis=dict(title="Total Mensal", range=[0, y_max]),
                xaxis=dict(title="Mês"),
                uniformtext_minsize=14,
                uniformtext_mode="hide"
            )
            st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------
# TAB 2 — Séries
# --------------------------------------------------------------------
with tab2:
    # ---- Pizzas ----
    total_producao   = safe_sum(df_filtro3.get("producao", pd.Series(dtype=float)))
    total_rejeito    = safe_sum(df_filtro3.get("rejeito", pd.Series(dtype=float)))
    total_produzindo = safe_sum(df_filtro3.get("produzindo", pd.Series(dtype=float)))
    total_parada     = safe_sum(df_filtro3.get("parada", pd.Series(dtype=float)))

    col9, col10 = st.columns(2)
    with col9:
        if total_producao == 0 and total_rejeito == 0:
            st.info("Sem dados para **Produção vs Rejeito**.")
        else:
            fig3 = go.Figure(
                data=[go.Pie(
                    labels=["Produção", "Rejeito"],
                    values=[total_producao, total_rejeito],
                    hole=0.4,
                    textinfo="label+value+percent",
                    textfont_size=16,
                    rotation=270  # começa às 6h (opcional)
                )]
            )
            fig3.update_layout(
                title_text=f"QUALIDADE - Prod x Rejeito - {str(month) if month is not None else ''}"
            )
            st.plotly_chart(fig3, use_container_width=True)

    with col10:
        if total_oee.empty:
            st.info("Sem dados para **Eficiência Mensal (OEE%)**.")
        else:
            fig6 = px.line(
                total_oee,
                x="month_label", y="oee",
                markers=True,
                text=total_oee["oee"].round(0),
                labels={"month_label": "Mês", "oee": "OEE (%)"},
                title="Eficiência Mensal da Moagem (OEE%)"
            )
            fig6.update_traces(textposition="top center")
            fig6.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig6, use_container_width=True)

    st.subheader("Performance")
    col13, col14 = st.columns(2)
    with col13:
        if df.empty or not {"produzindo", "parada"}.issubset(df.columns):
            st.info("Sem colunas suficientes para **Rodando vs Parada**.")
        else:
            resumo = df.groupby("month", as_index=False)[["produzindo", "parada"]].sum()
            resumo["month_label"] = resumo["month"].dt.strftime("%b %Y")
            melt = resumo.melt("month_label", ["produzindo", "parada"], "Status", "Minutos")
            melt["Status"] = melt["Status"].map({"produzindo": "Máquina Rodando", "parada": "Máquina Parada"})
            fig7 = px.line(
                melt, x="month_label", y="Minutos",
                color="Status", markers=True, text="Minutos",
                title="Total de Máquina Rodando vs Parada (min)",
                labels={"month_label": "Mês", "Minutos": "Minutos Totais"}
            )
            fig7.update_traces(textposition="top center")
            st.plotly_chart(fig7, use_container_width=True)

    with col14:
        if df.empty or not {"produzindo", "disponivel"}.issubset(df.columns):
            st.info("Sem colunas suficientes para **Disponível vs Rodando**.")
        else:
            resumo = df.groupby("month", as_index=False)[["produzindo", "disponivel"]].sum()
            resumo["month_label"] = resumo["month"].dt.strftime("%b %Y")
            melt = resumo.melt("month_label", ["produzindo", "disponivel"], "Status", "Minutos")
            melt["Status"] = melt["Status"].map({"produzindo": "Máquina Rodando", "disponivel": "Máquina Disponível"})
            fig8 = px.line(
                melt, x="month_label", y="Minutos",
                color="Status", markers=True, text="Minutos",
                title="Total de Máquina Disponível vs Rodando (min)",
                labels={"month_label": "Mês", "Minutos": "Minutos Totais"}
            )
            fig8.update_traces(textposition="top center")
            st.plotly_chart(fig8, use_container_width=True)

    # ====== PRODUTIVIDADE: produção (kg) x tempo (min) ======
    # Agrupa por mês
    res = (
        df_filtro1.copy()
        .assign(
            producao=pd.to_numeric(df_filtro1.get("producao", 0), errors="coerce"),
            produzindo=pd.to_numeric(df_filtro1.get("produzindo", 0), errors="coerce"),
        )
        .groupby("month", as_index=False)
        .agg(producao_kg=("producao", "sum"), tempo_min=("produzindo", "sum"))
    )

    if res.empty:
        st.info("Sem dados para montar Produção x Tempo.")
    else:
        res["month_label"] = res["month"].dt.strftime("%b %Y")
        res["horas"] = res["tempo_min"] / 60.0
        # KPIs
        res["kg_h"] = res.apply(lambda r: r["producao_kg"] / r["horas"] if r["horas"] > 0 else 0, axis=1)
        res["min_por_kg"] = res.apply(lambda r: r["tempo_min"] / r["producao_kg"] if r["producao_kg"] > 0 else 0, axis=1)

        st.subheader("Produção x Tempo (visões complementares)")
        colA, colB, colC = st.columns(3)

        # --- (1) Combo: Barra (kg) + Linha (h) com 2 eixos ---
        with colA:
            fig_combo = go.Figure()
            # Barra: Produção (kg)
            fig_combo.add_bar(
                x=res["month_label"],
                y=res["producao_kg"],
                name="Produção (kg)",
                text=[f"{v:,.0f}" for v in res["producao_kg"]],
                textposition="outside",
                hovertemplate="Mês: %{x}<br>Produção: %{y:,.0f} kg<extra></extra>",
            )
            # Linha: Tempo (h)
            horas = res["horas"]
            fig_combo.add_scatter(
                x=res["month_label"],
                y=horas,
                name="Tempo (h)",
                mode="lines+markers+text",
                text=[f"{v:,.1f}" for v in horas],
                textposition="top center",
                yaxis="y2",
                hovertemplate="Mês: %{x}<br>Tempo: %{y:,.1f} h<extra></extra>",
            )
            fig_combo.update_layout(
                title="Produção (kg) vs Tempo (h) por mês",
                xaxis_title="Mês",
                yaxis=dict(title="Produção (kg)"),
                yaxis2=dict(title="Tempo (h)", overlaying="y", side="right", range=[0, 600]),
                margin=dict(l=10, r=10, t=60, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_combo, use_container_width=True)

        # --- (2) KPI: kg/h ---
        with colB:
            fig_kpi = px.bar(
                res,
                x="month_label",
                y="kg_h",
                text="kg_h",
                title="Produtividade (kg/h) por mês",
                labels={"month_label": "Mês", "kg_h": "Produtividade (kg/h)"},
            )
            fig_kpi.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
            fig_kpi.update_layout(yaxis=dict(rangemode="tozero"), margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig_kpi, use_container_width=True)

        # --- (3) Barra Empilhada: tempo em 'kg-equivalente' ---
        with colC:
            total_kg = res["producao_kg"].sum()
            total_h  = res["horas"].sum()
            taxa_ref_kgh = total_kg / total_h if total_h > 0 else 0  # kg/h ref

            if taxa_ref_kgh == 0:
                st.info("Sem taxa de referência (kg/h) para empilhar tempo como kg-equivalente.")
            else:
                res["tempo_kg_equiv"] = res["horas"] * taxa_ref_kgh  # converte horas -> kg equivalente

                emp = res.rename(columns={
                    "producao_kg": "Produção (kg)",
                    "tempo_kg_equiv": "Tempo (kg equivalente)"
                })

                fig_emp = px.bar(
                    emp,
                    x="month_label",
                    y=["Produção (kg)", "Tempo (kg equivalente)"],
                    barmode="stack",
                    title=f"Produção real + Tempo/'kg-equivalente' (taxa ref: {taxa_ref_kgh:,.1f} kg/h)",
                    labels={"month_label": "Mês", "value": "kg", "variable": ""},
                    text_auto=".0f",
                )
                fig_emp.update_layout(
                    margin=dict(l=10, r=10, t=80, b=20),
                    legend_title_text="",
                    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
                )
                st.plotly_chart(fig_emp, use_container_width=True)

# --------------------------------------------------------------------
# TAB 3 — Tabela
# --------------------------------------------------------------------
with tab3:
    st.subheader(f"Detalhamento do mês selecionado: {str(month) if month is not None else '-'}")
    st.dataframe(df_filtro3, use_container_width=True)
