# =========================================================
# AXION - Moduli "Analiza" (Dashboard interaktiv)
# =========================================================
# Eksporton: render_analiza(df_raw)
#
# Replikon funksionalitetin e HTML dashboard-it origjinal (analiza.py)
# por nativ ne Streamlit me Plotly. Perdor df_raw qe eshte tashme i ngarkuar.
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


MUAJT_SQ = {
    1: "Jan", 2: "Shk", 3: "Mar", 4: "Pri",
    5: "Maj", 6: "Qer", 7: "Kor", 8: "Gus",
    9: "Sht", 10: "Tet", 11: "Nen", 12: "Dhj",
}


def render_analiza(df_raw):
    st.title("Analiza e Shitjeve")
    st.markdown("Dashboard interaktiv per trendet, kategorite dhe performancen e agjenteve.")

    if df_raw is None or df_raw.empty:
        st.error("Nuk u gjeten te dhena.")
        return

    df = df_raw.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df["Viti"] = df["Data"].dt.year
    df["Muaji_Nr"] = df["Data"].dt.month
    df["Muaji"] = df["Muaji_Nr"].map(MUAJT_SQ)

    # Identifiko kolonen e vleres
    vlera_col = None
    for cand in ["VleraRresht", "TotalRresht", "Vlera_Historike"]:
        if cand in df.columns:
            vlera_col = cand
            break
    if vlera_col is None:
        st.error("Nuk u gjet kolona e vleres (VleraRresht / TotalRresht).")
        return

    # Identifiko kolonen e kategorise
    kat_col = None
    for cand in ["kat", "Kategoria_Finale", "Kategoria"]:
        if cand in df.columns:
            kat_col = cand
            break

    # Sigurohu qe ka kolone "Sasia"
    sasia_col = "Sasia" if "Sasia" in df.columns else None

    # --- Switch metrike ---
    metric_label = st.radio(
        "Metrika:",
        ["Vlera (LEK)", "Pesha (KG)"],
        horizontal=True,
        key="anl_metric",
    )
    metric_col = vlera_col if metric_label == "Vlera (LEK)" else "kg"
    metric_emri = "Vlera" if metric_label == "Vlera (LEK)" else "KG"

    # --- Filtrat ---
    with st.expander("Filtra", expanded=True):
        c1, c2, c3, c4 = st.columns(4)

        vitet = sorted(df["Viti"].dropna().unique().tolist())
        sel_vitet = c1.multiselect("Viti", vitet, default=vitet[-2:] if len(vitet) > 1 else vitet)

        if "Grup_Filtri" in df.columns:
            grupet = sorted(df["Grup_Filtri"].dropna().unique().tolist())
            sel_grupet = c2.multiselect("Grupi", grupet, default=grupet)
        else:
            sel_grupet = None
            c2.caption("Pa kolone Grupi")

        agjentet = sorted(df["ForcaShitese"].dropna().astype(str).unique().tolist())
        sel_agjentet = c3.multiselect("Agjenti", agjentet, default=agjentet)

        if kat_col:
            kategorite = sorted(df[kat_col].dropna().astype(str).unique().tolist())
            sel_kat = c4.multiselect("Kategoria", kategorite, default=kategorite)
        else:
            sel_kat = None
            c4.caption("Pa kolone Kategorie")

    # --- Apliko filtrat ---
    df_f = df[df["Viti"].isin(sel_vitet) & df["ForcaShitese"].astype(str).isin(sel_agjentet)]
    if sel_grupet is not None:
        df_f = df_f[df_f["Grup_Filtri"].isin(sel_grupet)]
    if sel_kat is not None and kat_col:
        df_f = df_f[df_f[kat_col].astype(str).isin(sel_kat)]

    if df_f.empty:
        st.warning("Asnje e dhene per filtrat e zgjedhur.")
        return

    # --- KPI metrika ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Vlera (LEK)", "{:,.0f}".format(df_f[vlera_col].sum()))
    m2.metric("Total KG", "{:,.0f}".format(df_f["kg"].sum()))
    if sasia_col:
        m3.metric("Total Sasia", "{:,.0f}".format(df_f[sasia_col].sum()))
    else:
        m3.metric("Klientet Unike", df_f["Klienti"].nunique() if "Klienti" in df_f.columns else 0)

    st.divider()

    # --- Trendi Kohor ---
    st.subheader("Trendi Kohor")
    if len(sel_vitet) == 1:
        trend = df_f.groupby("Muaji_Nr")[metric_col].sum().reset_index()
        trend["Muaji"] = trend["Muaji_Nr"].map(MUAJT_SQ)
        fig = px.line(
            trend, x="Muaji", y=metric_col,
            markers=True,
            title="Ecuria: " + str(sel_vitet[0]),
        )
        fig.update_traces(line=dict(width=3))
        fig.update_layout(yaxis_title=metric_emri, xaxis_title="Muaji")
    else:
        trend = df_f.groupby(["Viti", "Muaji_Nr"])[metric_col].sum().reset_index()
        trend["Muaji"] = trend["Muaji_Nr"].map(MUAJT_SQ)
        trend["Viti"] = trend["Viti"].astype(str)
        fig = px.line(
            trend, x="Muaji", y=metric_col, color="Viti",
            markers=True, title="Krahasimi Vjetor",
        )
        fig.update_traces(line=dict(width=2))
        fig.update_layout(yaxis_title=metric_emri, xaxis_title="Muaji")
    st.plotly_chart(fig, use_container_width=True)

    # --- Dy kolona: Pie + Top Kategorite ---
    if kat_col:
        col_pie, col_tab = st.columns([1, 1])

        with col_pie:
            st.subheader("Ndarja sipas Kategorive")
            pie = df_f.groupby(kat_col)[metric_col].sum().reset_index()
            pie = pie.sort_values(metric_col, ascending=False).head(10)
            fig_pie = px.pie(
                pie, values=metric_col, names=kat_col,
                hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_tab:
            st.subheader("Top Kategorite")
            agg_dict = {"Vlera": (vlera_col, "sum"), "KG": ("kg", "sum")}
            if sasia_col:
                agg_dict["Sasia"] = (sasia_col, "sum")
            top_kat = (
                df_f.groupby(kat_col)
                .agg(**agg_dict)
                .sort_values("Vlera", ascending=False)
                .reset_index()
                .head(15)
            )
            top_kat.columns = ["Kategoria"] + list(top_kat.columns[1:])
            fmt = {"Vlera": "{:,.0f}", "KG": "{:,.0f}"}
            if "Sasia" in top_kat.columns:
                fmt["Sasia"] = "{:,.0f}"
            st.dataframe(
                top_kat.style.format(fmt),
                use_container_width=True,
                hide_index=True,
                height=400,
            )

    # --- Performanca Agjenteve ---
    st.subheader("Performanca Agjenteve")
    top_agj = (
        df_f.groupby("ForcaShitese")
        .agg(
            Vlera=(vlera_col, "sum"),
            KG=("kg", "sum"),
            Klientet=("Klienti", "nunique") if "Klienti" in df_f.columns else (vlera_col, "count"),
        )
        .sort_values("Vlera", ascending=False)
        .reset_index()
    )
    top_agj.columns = ["Agjenti", "Vlera", "KG", "Klientet"]

    fig_bar = px.bar(
        top_agj.head(20), x="Agjenti", y="Vlera" if metric_emri == "Vlera" else "KG",
        title="Top 20 Agjente sipas " + metric_emri,
        color="Vlera" if metric_emri == "Vlera" else "KG",
        color_continuous_scale="Blues",
    )
    fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False, height=450)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(
        top_agj.style.format({
            "Vlera": "{:,.0f}",
            "KG": "{:,.0f}",
            "Klientet": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # --- Eksporti ---
    st.divider()
    col_e1, col_e2 = st.columns(2)
    csv_kat = (
        df_f.groupby(kat_col if kat_col else "ForcaShitese")
        .agg(Vlera=(vlera_col, "sum"), KG=("kg", "sum"))
        .sort_values("Vlera", ascending=False)
        .reset_index()
        .to_csv(index=False)
        .encode("utf-8-sig")
    )
    col_e1.download_button(
        "Shkarko Permbledhjen e Kategorive (CSV)",
        csv_kat,
        "analiza_kategorite.csv",
        "text/csv",
        use_container_width=True,
    )
    csv_agj = top_agj.to_csv(index=False).encode("utf-8-sig")
    col_e2.download_button(
        "Shkarko Permbledhjen e Agjenteve (CSV)",
        csv_agj,
        "analiza_agjentet.csv",
        "text/csv",
        use_container_width=True,
    )
