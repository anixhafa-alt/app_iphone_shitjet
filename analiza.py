import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def render_analiza_klienteve(df_raw):
    st.title("📊 Dashboard Ekzekutiv i Shitjeve")
    st.markdown(
        "Analizë e detajuar e shitjeve, volumit në KG dhe kategorive të produkteve."
    )

    if df_raw is None or df_raw.empty:
        st.error("❌ Nuk u gjetën të dhëna valide nga skedari SAD-DATAbase1.xlsb.")
        return

    # --- 1. PASTRIMI DHE FORMATIMI I TË DHËNAVE ---
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.replace('"', "")

    # Konvertimi i Datës
    if pd.api.types.is_numeric_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], unit="D", origin="1899-12-30")
    else:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    df = df.dropna(subset=["Data"])

    # Konvertimet numerike kritike
    cols_numerike = ["TotalRresht", "Sasia", "kg"]
    for c in cols_numerike:
        if c in df.columns:
            if df[c].dtype == "object":
                df[c] = df[c].astype(str).str.replace(",", "", regex=False)
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0.0

    # Krijimi i kolonave të kohës
    df["Viti"] = df["Data"].dt.year.astype(int)
    df["Muaji_Nr"] = df["Data"].dt.month.astype(int)

    muajt_shqip = {
        1: "Janar",
        2: "Shkurt",
        3: "Mars",
        4: "Prill",
        5: "Maj",
        6: "Qershor",
        7: "Korrik",
        8: "Gusht",
        9: "Shtator",
        10: "Tetor",
        11: "Nëntor",
        12: "Dhjetor",
    }
    df["Muaji"] = df["Muaji_Nr"].map(muajt_shqip)

    if "Kategoria_Finale" not in df.columns:
        if "KATEG." in df.columns:
            df["Kategoria_Finale"] = df["KATEG."]
        else:
            df["Kategoria_Finale"] = "ETJ"

    # --- 2. FILTRAT DIREKT NË STREAMLIT (Pa JS që bën crash) ---
    st.sidebar.markdown("### 🎛️ Filtrat e Dashboard-it")

    vitet_opsione = sorted(df["Viti"].unique(), reverse=True)
    viti_sel = st.sidebar.selectbox(
        "Zgjidh Vitin", ["Gjithë Vitet"] + list(vitet_opsione)
    )

    muajt_opsione = [
        "Janar",
        "Shkurt",
        "Mars",
        "Prill",
        "Maj",
        "Qershor",
        "Korrik",
        "Gusht",
        "Shtator",
        "Tetor",
        "Nëntor",
        "Dhjetor",
    ]
    muaji_sel = st.sidebar.selectbox("Zgjidh Muajin", ["Gjithë Muajt"] + muajt_opsione)

    agjentet_opsione = sorted(df["ForcaShitese"].astype(str).unique())
    agjent_sel = st.sidebar.selectbox(
        "Zgjidh Agjentin", ["Gjithë Agjentët"] + list(agjentet_opsione)
    )

    metrika_sel = st.sidebar.radio("Zgjidh Metrikën", ["Lek (Vlerë)", "KG (Volum)"])
    kolona_metrike = "TotalRresht" if metrika_sel == "Lek (Vlerë)" else "kg"

    # Aplikimi i filtrave mbi DataFrame
    df_filtered = df.copy()
    if viti_sel != "Gjithë Vitet":
        df_filtered = df_filtered[df_filtered["Viti"] == int(viti_sel)]
    if muaji_sel != "Gjithë Muajt":
        df_filtered = df_filtered[df_filtered["Muaji"] == muaji_sel]
    if agjent_sel != "Gjithë Agjentët":
        df_filtered = df_filtered[df_filtered["ForcaShitese"] == agjent_sel]

    # --- 3. SHFAQA E KPI-ve ---
    total_vlerë = df_filtered[kolona_metrike].sum()
    faturat_count = len(df_filtered)
    kliente_unik = df_filtered["Klienti"].nunique()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label=f"{metrika_sel} Total", value=f"{total_vlerë:,.2f}")
    with col2:
        st.metric(label="Numri i Transaksioneve", value=f"{faturat_count:,}")
    with col3:
        st.metric(label="Klientë Aktivë", value=f"{kliente_unik:,}")

    st.markdown("---")

    # --- 4. GRAFIKËT REALIZUAR ME PLOTLY (Native & Fast) ---
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📈 Ecuria sipas Muajve")
        # Agregimi sipas Vitit dhe Muajit për grafikun linear
        df_line = (
            df_filtered.groupby(["Viti", "Muaji_Nr", "Muaji"])[kolona_metrike]
            .sum()
            .reset_index()
        )
        df_line = df_line.sort_values(by=["Viti", "Muaji_Nr"])

        fig_line = px.line(
            df_line,
            x="Muaji",
            y=kolona_metrike,
            color=df_line["Viti"].astype(str),
            markers=True,
            labels={kolona_metrike: metrika_sel, "x": "Muaji"},
            template="plotly_white",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with col_g2:
        st.subheader("🍕 Ndarja sipas Kategorive")
        df_pie = (
            df_filtered.groupby("Kategoria_Finale")[kolona_metrike].sum().reset_index()
        )

        fig_pie = px.pie(
            df_pie,
            values=kolona_metrike,
            names="Kategoria_Finale",
            hole=0.4,
            template="plotly_white",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- 5. TABELA DINAMIKE (Top 15 Klientët ose Agjentët) ---
    st.markdown("---")
    shfaq_klientet = agjent_sel != "Gjithë Agjentët" or len(df_filtered) < 2000

    if shfaq_klientet:
        st.subheader("🏆 Top 15 Klientët më të Mëdhenj")
        kolona_grupimi = "Klienti"
    else:
        st.subheader("💼 Renditja e Agjentëve (Forca Shitëse)")
        kolona_grupimi = "ForcaShitese"

    df_table = df_filtered.groupby(kolona_grupimi)[kolona_metrike].sum().reset_index()
    df_table = (
        df_table.sort_values(
            by=metrika_sel if metrika_sel in df_table.columns else kolona_metrike,
            ascending=False,
        )
        .head(15)
        .reset_index(drop=True)
    )
    df_table.index = df_table.index + 1  # Renditja fillon nga 1

    # Formatimi i kolonës së parave/volumit për tabelë
    df_table[metrika_sel] = df_table[kolona_metrike].map("{:,.2f}".format)

    st.dataframe(df_table[[kolona_grupimi, metrika_sel]], use_container_width=True)
