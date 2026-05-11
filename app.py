import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

@st.cache_data
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Shtojmë kolonën 'Vlera' ose 'Cmimi' nëse i ke në Excel për pikën 7
    # Po supozoj që kolonat janë: Data, ForcaShitese, Klienti, Artikulli, kg, kat, VleraNeto
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat']
    df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
    df.columns = df.columns.str.strip().str.replace('"', '')
    df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
    return df

df = load_data()

if df is not None:
    # --- SIDEBAR (Pika 4 dhe 8) ---
    st.sidebar.header("Konfigurimi i Planit")
    
    # Pika 4: Zgjedhja e periudhës referente
    min_date = df['Data'].min().date()
    max_date = df['Data'].max().date()
    start_date, end_date = st.sidebar.date_input(
        "Periudha referente për llogaritje:",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Pika 8: Kuti për rritjen në %
    rritja_perqindje = st.sidebar.number_input("Përcakto rritjen e planit (%)", min_value=-100, max_value=500, value=10)

    # --- FILTRAT (Pika 3 dhe 6) ---
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti_select = st.sidebar.selectbox("Zgjidh Agjentin (Pika 3):", ["Të gjithë"] + agj_list)
    
    search_klient = st.sidebar.text_input("Kërko Klientin (Pika 6):")

    # --- PROCESIMI I TË DHËNAVE ---
    # Filtrojmë sipas periudhës referente
    mask = (df['Data'].date >= start_date) & (df['Data'].date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti_select != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti_select]
    
    if search_klient:
        dff = dff[dff['Klienti'].str.contains(search_klient, case=False, na=False)]

    # Llogarisim muajt e periudhës referente
    n_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if n_months <= 0: n_months = 1

    # --- PIKA 5: Titulli me Muajin/Vitin e Planit ---
    next_month_date = end_date + pd.DateOffset(months=1)
    st.title(f"🎯 Plani i Shitjeve: {next_month_date.strftime('%B %Y')}")
    st.caption(f"Bazuar në periudhën: {start_date} deri {end_date} ({n_months} muaj referencë)")

    # --- LLOGARITJET ---
    # Grupimi bazë (Pika 2 dhe 6)
    gp = dff.groupby(['ForcaShitese', 'kat', 'Artikulli']).agg({'kg': 'sum'}).reset_index()
    
    # Kalkulimi i planit mujor me rritjen (Pika 8)
    gp['Mesatarja_Referente'] = gp['kg'] / n_months
    gp['Plani_i_Ri_KG'] = (gp['Mesatarja_Referente'] * (1 + rritja_perqindje/100)).round(1)

    # --- PIKA 1: Totalet ---
    total_kg_referent = gp['kg'].sum()
    total_plani_kg = gp['Plani_i_Ri_KG'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total KG (Referenca)", f"{total_kg_referent:,.1f}")
    col2.metric(f"Plani i ri (+{rritja_perqindje}%)", f"{total_plani_kg:,.1f} KG")
    col3.metric("Nr. Artikujve", len(gp['Artikulli'].unique()))

    # --- SHFAQJA E PLANIT (Pika 2, 3, 6) ---
    if search_klient:
        st.subheader(f"Plani i detajuar për: {search_klient}")
        # Grupimi sipas Kategorive dhe Artikujve (Pika 2 dhe 6)
        st.dataframe(gp[['kat', 'Artikulli', 'Plani_i_Ri_KG']], use_container_width=True, hide_index=True)
    else:
        # Shfaqja e përgjithshme e grupuar (Pika 2 dhe 3)
        tab1, tab2 = st.tabs(["Sipas Kategorive", "Sipas Agjentëve"])
        with tab1:
            kat_summary = gp.groupby('kat')['Plani_i_Ri_KG'].sum().reset_index()
            st.dataframe(kat_summary, use_container_width=True)
        with tab2:
            agj_summary = gp.groupby('ForcaShitese')['Plani_i_Ri_KG'].sum().reset_index()
            st.dataframe(agj_summary, use_container_width=True)

    # Shënim për pikën 7: Çmimi mesatar kërkon kolonën 'Vlera' në Excel.
    # Nëse e shton, mund të llogarisim: gp['Cmimi_Mesatar'] = gp['Vlera'] / gp['kg']