import streamlit as st
import pandas as pd

# 1. Konfigurimi
st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

@st.cache_data
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Shto kolonën 'Vlera' ose 'Cmimi' nëse i ke në Excel për pikën 7
    # Nëse emrat ndryshojnë, përshtati te lista më poshtë
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat']
    
    try:
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip().str.replace('"', '')
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        return df
    except Exception as e:
        st.error(f"Gabim në lexim: {e}")
        return None

df = load_data()

if df is not None:
    # --- SIDEBAR (Pika 4 & 8) ---
    st.sidebar.header("⚙️ Parametrat e Planit")
    
    # Pika 4: Periudha referente (Rregulluar)
    min_date = df['Data'].min().date()
    max_date = df['Data'].max().date()
    
    date_range = st.sidebar.date_input(
        "Periudha referente:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Sigurohemi që janë zgjedhur dy data
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # Pika 8: Rritja në %
    rritja_perqindje = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # --- FILTRAT (Pika 3 & 6) ---
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti_select = st.sidebar.selectbox("Agjenti (Pika 3):", ["Të gjithë"] + agj_list)
    
    search_klient = st.sidebar.text_input("Kërko Klientin (Pika 6):")

    # --- FILTRIMI I TË DHËNAVE (Rregullimi i Maskës) ---
    # Përdorim .dt.date për krahasimin e kolonës me start_date/end_date
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti_select != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti_select]
    
    if search_klient:
        dff = dff[dff['Klienti'].str.contains(search_klient, case=False, na=False)]

    # Llogaritja e muajve (Pika 4)
    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- DISPLAY ---
    # Pika 5: Titulli dinamik
    next_month = (pd.to_datetime(end_date) + pd.DateOffset(months=1))
    st.title(f"🎯 Plani: {next_month.strftime('%B %Y')}")
    st.caption(f"Bazuar në: {start_date} deri {end_date} ({n_months} muaj)")

    # Agregimi (Pika 2, 3, 6)
    # Këtu llogarisim totalet për çdo kombinim
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({'kg': 'sum'}).reset_index()
    
    # Kalkulimi i Planit (Pika 8)
    gp['Mesatarja_Mujore'] = (gp['kg'] / n_months)
    gp['Plani_KG'] = (gp['Mesatarja_Mujore'] * (1 + rritja_perqindje/100)).round(1)

    # Pika 1: Totalet në KRYE
    c1, c2, c3 = st.columns(3)
    c1.metric("Total KG Referenca", f"{gp['kg'].sum():,.0f}")
    c2.metric(f"Plani i Ri (+{rritja_perqindje}%)", f"{gp['Plani_KG'].sum():,.0f}")
    c3.metric("Nr. Artikujve", f"{gp['Artikulli'].nunique()}")

    # SHFAQJA E GRUPUAR
    st.divider()
    
    if search_klient:
        # Pika 6: Plani i detajuar për klientin
        st.subheader(f"📍 Detajet për: {search_klient}")
        # Grupimi sipas Kategorisë dhe Artikullit
        klient_view = gp.groupby(['kat', 'Artikulli'])['Plani_KG'].sum().reset_index()
        st.dataframe(klient_view, use_container_width=True, hide_index=True)
    else:
        # Pamja e përgjithshme me Tabs
        t1, t2 = st.tabs(["Sipas Kategorive (Pika 2)", "Sipas Agjentëve (Pika 3)"])
        
        with t1:
            kat_view = gp.groupby('kat')['Plani_KG'].sum().reset_index().sort_values('Plani_KG', ascending=False)
            st.dataframe(kat_view, use_container_width=True, hide_index=True)
            
        with t2:
            agj_view = gp.groupby('ForcaShitese')['Plani_KG'].sum().reset_index().sort_values('Plani_KG', ascending=False)
            st.dataframe(agj_view, use_container_width=True, hide_index=True)

    # Shënim për pikën 7 (Çmimi):
    # Nëse dëshiron çmimin e fundit, do të duhej një kolonë 'Vlera' ose 'Cmimi' 
    # dhe një renditje sipas datës për të marrë vlerën e rreshtit të fundit.