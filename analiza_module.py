# =========================================================
# AXION - Moduli "Analiza" (Dashboard interaktiv)
# =========================================================
# Eksporton: render_analiza()
#
# Lexon te dhenat me prioritet Parquet (i shpejte) > XLSB (i ngadalte).
# Per te konvertuar XLSB ne Parquet, ekzekuto LOKALISHT:
#     python convert_xlsb_to_parquet.py
#
# DEPENDENCE: pyxlsb, pyarrow (te dyja te requirements.txt)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os


FILE_NAME_XLSB = "SAD-DATAbase1.xlsb"
FILE_NAME_PARQUET = "SAD-DATAbase1.parquet"

MUAJT_SQ = {
    1: "Jan", 2: "Shk", 3: "Mar", 4: "Pri",
    5: "Maj", 6: "Qer", 7: "Kor", 8: "Gus",
    9: "Sht", 10: "Tet", 11: "Nen", 12: "Dhj",
}


def _pastro_te_dhenat(df):
    """Aplikon pastrimet e nevojshme. Punon edhe per XLSB, edhe per Parquet."""
    df.columns = df.columns.str.strip().str.replace('"', "", regex=False)

    if "Data" not in df.columns:
        return None, "Kolona 'Data' nuk u gjet."

    # Data mund te jete numerike (Excel serial) ose tekst — provo te dyja
    if pd.api.types.is_numeric_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], unit="D", origin="1899-12-30")
    elif not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    df = df.dropna(subset=["Data"])
    df = df[df["Data"].dt.year >= 2000]

    for col in ["TotalRresht", "Sasia", "kg"]:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace(",", "", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0.0

    df["Kategoria_Finale"] = "Tjera"
    if "Kategoria" in df.columns:
        df["Kategoria"] = df["Kategoria"].astype(str).replace("nan", "")
        if "GrupiArtikullit" in df.columns:
            df["GrupiArtikullit"] = df["GrupiArtikullit"].astype(str).replace("nan", "")
            df["Kategoria_Finale"] = np.where(
                df["Kategoria"] == "",
                df["GrupiArtikullit"],
                df["Kategoria"],
            )
        else:
            df["Kategoria_Finale"] = df["Kategoria"]
    elif "GrupiArtikullit" in df.columns:
        df["Kategoria_Finale"] = df["GrupiArtikullit"].fillna("Tjera").astype(str)
    df["Kategoria_Finale"] = df["Kategoria_Finale"].replace(["", "nan", "0"], "Tjera")

    if "Supervizori" not in df.columns:
        df["Supervizori"] = "Pa Caktuar"
    else:
        df["Supervizori"] = df["Supervizori"].fillna("Pa Caktuar").astype(str)

    if "Anulluar" in df.columns:
        df = df[df["Anulluar"].astype(str).str.lower() != "true"]

    df = df[(df["TotalRresht"] > 0) | (df["kg"] > 0)]

    df["Viti"] = df["Data"].dt.year
    df["Muaji_Nr"] = df["Data"].dt.month
    df["Muaji"] = df["Muaji_Nr"].map(MUAJT_SQ)

    return df, None


@st.cache_data(ttl=3600, show_spinner="Duke ngarkuar te dhenat...")
def _ngarko_te_dhenat():
    """Prefero Parquet > XLSB. Cache 1 ore."""
    if os.path.exists(FILE_NAME_PARQUET):
        try:
            df = pd.read_parquet(FILE_NAME_PARQUET)
            return _pastro_te_dhenat(df) + ("parquet",)
        except ImportError:
            pass
        except Exception as e:
            st.warning("Parquet u prish, po lexoj XLSB. Detaji: " + str(e))

    if not os.path.exists(FILE_NAME_XLSB):
        return None, "Asnjeri prej skedareve nuk u gjet: '" + FILE_NAME_PARQUET + "' ose '" + FILE_NAME_XLSB + "'.", "none"

    try:
        df = pd.read_excel(FILE_NAME_XLSB, engine="pyxlsb", sheet_name="Sheet1")
    except ImportError:
        return None, "Paketa 'pyxlsb' mungon. Shto 'pyxlsb' te requirements.txt.", "none"
    except Exception as e:
        return None, "Gabim gjate leximit te XLSB: " + str(e), "none"

    return _pastro_te_dhenat(df) + ("xlsb",)


def render_analiza():
    st.title("Analiza e Shitjeve")
    st.markdown("Dashboard interaktiv per trendet, kategorite dhe performancen e agjenteve.")

    df, err, burimi = _ngarko_te_dhenat()
    if err:
        st.error(err)
        st.info(
            "Per perfomance: konverto XLSB ne Parquet (50-100x me shpejt). "
            "Ekzekuto lokalisht: `python convert_xlsb_to_parquet.py` "
            "pastaj bej push te SAD-DATAbase1.parquet."
        )
        return
    if df is None or df.empty:
        st.error("Skedari u lexua, por nuk ka te dhena te vlefshme.")
        return

    if burimi == "parquet":
        st.caption("Burimi: Parquet (i shpejte) - {:,} rreshta".format(len(df)))
    else:
        st.caption("Burimi: XLSB - {:,} rreshta. Konsidero konvertimin ne Parquet.".format(len(df)))

    metric_label = st.radio(
        "Metrika:",
        ["Vlera (LEK)", "Pesha (KG)"],
        horizontal=True,
        key="anl_metric",
    )
    metric_col = "TotalRresht" if metric_label == "Vlera (LEK)" else "kg"
    metric_emri = "Vlera" if metric_label == "Vlera (LEK)" else "KG"

    with st.expander("Filtra", expanded=True):
        c1, c2, c3, c4 = st.columns(4)

        vitet = sorted(df["Viti"].dropna().unique().tolist())
        default_vitet = vitet[-2:] if len(vitet) > 1 else vitet
        sel_vitet = c1.multiselect("Viti", vitet, default=default_vitet)

        df_pf = df[df["Viti"].isin(sel_vitet)] if sel_vitet else df
        supervizoret = sorted(df_pf["Supervizori"].dropna().unique().tolist())
        sel_sup = c2.multiselect("Rajoni (Supervizori)", supervizoret, default=supervizoret)

        if "ForcaShitese" in df.columns:
            df_pf2 = df_pf[df_pf["Supervizori"].isin(sel_sup)] if sel_sup else df_pf
            agjentet = sorted(df_pf2["ForcaShitese"].dropna().astype(str).unique().tolist())
            sel_agj = c3.multiselect("Agjenti", agjentet, default=agjentet)
        else:
            sel_agj = None
            c3.caption("Pa kolone ForcaShitese")

        df_pf3 = df_pf
        if sel_sup:
            df_pf3 = df_pf3[df_pf3["Supervizori"].isin(sel_sup)]
        if sel_agj is not None:
            df_pf3 = df_pf3[df_pf3["ForcaShitese"].astype(str).isin(sel_agj)]
        kategorite = sorted(df_pf3["Kategoria_Finale"].dropna().astype(str).unique().tolist())
        sel_kat = c4.multiselect("Kategoria", kategorite, default=kategorite)

    df_f = df.copy()
    if sel_vitet:
        df_f = df_f[df_f["Viti"].isin(sel_vitet)]
    if sel_sup:
        df_f = df_f[df_f["Supervizori"].isin(sel_sup)]
    if sel_agj is not None:
        df_f = df_f[df_f["ForcaShitese"].astype(str).isin(sel_agj)]
    if sel_kat:
        df_f = df_f[df_f["Kategoria_Finale"].astype(str).isin(sel_kat)]

    if df_f.empty:
        st.warning("Asnje e dhene per filtrat e zgjedhur.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Vlera (LEK)", "{:,.0f}".format(df_f["TotalRresht"].sum()))
    m2.metric("Total KG", "{:,.0f}".format(df_f["kg"].sum()))
    m3.metric("Total Sasia", "{:,.0f}".format(df_f["Sasia"].sum()))
    m4.metric("Numri Rreshtave", "{:,.0f}".format(len(df_f)))

    st.divider()

    st.subheader("Trendi Kohor")
    if len(sel_vitet) == 1:
        trend = df_f.groupby("Muaji_Nr")[metric_col].sum().reset_index()
        trend["Muaji"] = trend["Muaji_Nr"].map(MUAJT_SQ)
        fig = px.line(trend, x="Muaji", y=metric_col, markers=True,
                      title="Ecuria: " + str(sel_vitet[0]))
        fig.update_traces(line=dict(width=3, color="#2ecc71"))
        fig.update_layout(yaxis_title=metric_emri, xaxis_title="Muaji", height=400)
    else:
        trend = df_f.groupby(["Viti", "Muaji_Nr"])[metric_col].sum().reset_index()
        trend["Muaji"] = trend["Muaji_Nr"].map(MUAJT_SQ)
        trend["Viti"] = trend["Viti"].astype(str)
        fig = px.line(trend, x="Muaji", y=metric_col, color="Viti", markers=True,
                      title="Krahasimi Vjetor")
        fig.update_traces(line=dict(width=2))
        fig.update_layout(yaxis_title=metric_emri, xaxis_title="Muaji", height=400)
    st.plotly_chart(fig, use_container_width=True)

    col_pie, col_tab = st.columns([1, 1])
    with col_pie:
        st.subheader("Ndarja sipas Kategorive")
        pie = df_f.groupby("Kategoria_Finale")[metric_col].sum().reset_index()
        pie = pie.sort_values(metric_col, ascending=False).head(10)
        fig_pie = px.pie(pie, values=metric_col, names="Kategoria_Finale", hole=0.4)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_tab:
        st.subheader("Top Kategorite")
        top_kat = (
            df_f.groupby("Kategoria_Finale")
            .agg(Vlera=("TotalRresht", "sum"),
                 KG=("kg", "sum"),
                 Sasia=("Sasia", "sum"))
            .sort_values("Vlera", ascending=False)
            .reset_index()
            .head(15)
        )
        top_kat.columns = ["Kategoria", "Vlera", "KG", "Sasia"]
        st.dataframe(
            top_kat.style.format({"Vlera": "{:,.0f}", "KG": "{:,.0f}", "Sasia": "{:,.0f}"}),
            use_container_width=True, hide_index=True, height=400,
        )

    if "ForcaShitese" in df_f.columns:
        st.subheader("Performanca Agjenteve")
        top_agj = (
            df_f.groupby("ForcaShitese")
            .agg(Vlera=("TotalRresht", "sum"), KG=("kg", "sum"))
            .sort_values("Vlera", ascending=False)
            .reset_index()
        )
        top_agj.columns = ["Agjenti", "Vlera", "KG"]
        bar_y = "Vlera" if metric_emri == "Vlera" else "KG"
        fig_bar = px.bar(top_agj.head(20), x="Agjenti", y=bar_y,
                         title="Top 20 Agjente sipas " + metric_emri,
                         color=bar_y, color_continuous_scale="Blues")
        fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False, height=450)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.dataframe(
            top_agj.style.format({"Vlera": "{:,.0f}", "KG": "{:,.0f}"}),
            use_container_width=True, hide_index=True,
        )
    else:
        top_agj = pd.DataFrame()

    st.subheader("Performanca sipas Rajonit (Supervizori)")
    top_sup = (
        df_f.groupby("Supervizori")
        .agg(Vlera=("TotalRresht", "sum"), KG=("kg", "sum"))
        .sort_values("Vlera", ascending=False)
        .reset_index()
    )
    top_sup.columns = ["Supervizori", "Vlera", "KG"]
    st.dataframe(
        top_sup.style.format({"Vlera": "{:,.0f}", "KG": "{:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

    st.divider()
    col_e1, col_e2, col_e3 = st.columns(3)
    csv_kat = top_kat.to_csv(index=False).encode("utf-8-sig")
    col_e1.download_button("Shkarko Kategorite (CSV)", csv_kat,
                           "analiza_kategorite.csv", "text/csv",
                           use_container_width=True)
    if not top_agj.empty:
        csv_agj = top_agj.to_csv(index=False).encode("utf-8-sig")
        col_e2.download_button("Shkarko Agjentet (CSV)", csv_agj,
                               "analiza_agjentet.csv", "text/csv",
                               use_container_width=True)
    csv_sup = top_sup.to_csv(index=False).encode("utf-8-sig")
    col_e3.download_button("Shkarko Rajonet (CSV)", csv_sup,
                           "analiza_rajonet.csv", "text/csv",
                           use_container_width=True)
