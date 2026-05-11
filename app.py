import streamlit as st
import pandas as pd

# 1. Konfigurimi i faqes
st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

@st.cache_data
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Përdorim 'VleraRresht' siç e kërkove
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip().str.replace('"', '')
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        # Llogarisim çmimin për çdo rresht (VleraRresht / kg)
        # Shtojmë një kontroll për të shmangur pjesëtimin me zero
        df['Cmimi_Rreshtit'] = df['VleraRresht'] / df['kg'].replace(0, 1)
        return df
    except Exception as e:
        st.error(f"Gabim në lexim: Sigurohu që kolona quhet saktë 'VleraRresht'. Error: {e}")
        return None

df = load_data()

if df is not None:
    # --- LOGJIKA E ÇMIMIT TË FUNDIT ---
    # Gjejmë çmimin e fundit të shitjes për çdo artikull në të gjithë historikun
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')
    last_prices = last_prices[['Artikulli', 'Cmimi_Rreshtit']].rename(columns={'Cmimi_Rreshtit': 'Cmimi_Fundit'})

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Parametrat")
    
    # Periudha referente për KG
    min_d = df['Data'].min().date()
    max_d = df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente për KG:", value=(min_d, max_d))
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_d, max_d

    rritja_perqindje = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # Filtrat
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti_select = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    search_klient = st.sidebar.text_input("Kërko Klientin:")

    # --- FILTRIMI I TË DHËNAVE ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti_select != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti_select]
    if search_klient:
        dff = dff[dff['Klienti'].str.contains(search_klient, case=False, na=False)]

    # Llogaritja e muajve (n_months)
    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- AGREGIMI DHE PLANIFIKIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({'kg': 'sum'}).reset_index()
    
    # Bashkojmë me çmimet e fundit
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Kalkulimet finale
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja_perqindje/100)).round(1)
    gp['Vlera_Planifikuar'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(2)

    # --- SHFAQJA ---
    st.title("📊 Plani i Shitjeve me Çmimin e Fundit")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total KG Referenca", f"{gp['kg'].sum():,.0f}")
    c2.metric(f"Plani KG (+{rritja_perqindje}%)", f"{gp['Plani_KG'].sum():,.0f}")
    c3.metric("Vlera e Planit (Lekë)", f"{gp['Vlera_Planifikuar'].sum():,.0f}")

    st.divider()

    if search_klient:
        st.subheader(f"📍 Detajet: {search_klient}")
        st.dataframe(gp[['kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Planifikuar']], 
                     use_container_width=True, hide_index=True)
    else:
        t1, t2, t3 = st.tabs(["Sipas Kategorive", "Sipas Agjentëve", "Sipas Klientëve"])
        
        with t1:
            kat_v = gp.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            st.dataframe(kat_v.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)
            
        with t2:
            agj_v = gp.groupby('ForcaShitese').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            st.dataframe(agj_v.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)

        with t3:
            klient_v = gp.groupby(['Klienti', 'ForcaShitese']).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            st.dataframe(klient_v.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)