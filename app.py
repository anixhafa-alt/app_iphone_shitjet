import streamlit as st
import pandas as pd

st.set_page_config(page_title="Plani Shitjeve", layout="wide")

@st.cache_data(ttl=600)
def load_data_safe():
    file_name = 'SAD-DATAbase1.xlsb'
    # Lexojmë vetëm kolonat që na duhen vërtet
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        # Lexojmë skedarin
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        
        # 1. Pastrojmë emrat e kolonave menjëherë
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # 2. KONVERTIMI I TIPIT (Ky hap kursen 80% të RAM-it)
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        df['ForcaShitese'] = df['ForcaShitese'].astype('category')
        df['kat'] = df['kat'].astype('category')
        
        # 3. LLOGARISIM ÇMIMIN DHE FSHIJMË KOLONËN E RËNDË
        df['Cmimi'] = (df['VleraRresht'] / df['kg'].replace(0, 1)).astype('float32')
        df.drop(columns=['VleraRresht'], inplace=True)
        
        # 4. KTHEJMË ÇDO GJË TJETËR NË STR DHE PASTRON RAM-in
        df['Klienti'] = df['Klienti'].astype(str)
        df['Artikulli'] = df['Artikulli'].astype(str)
        
        return df
    except Exception as e:
        st.error(f"Gabim kritik në memorje: {e}")
        return None

df = load_data_safe()

if df is not None:
    # LLOGARITJA E ÇMIMIT TË FUNDIT (Mënyra e shpejtë)
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi']]
    last_prices.rename(columns={'Cmimi': 'Cmimi_Fundit'}, inplace=True)

    # SIDEBAR
    st.sidebar.header("⚙️ Parametrat")
    rritja = st.sidebar.number_input("Rritja (%)", value=10)
    
    # Filtra të shpejtë
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x != 'nan'])
    agj_sel = st.sidebar.selectbox("Agjenti:", ["Të gjithë"] + agj_list)
    
    # Filtri i klientëve (limiton memorjen duke treguar vetëm unikët)
    k_list = df[df['ForcaShitese'].astype(str) == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df['Klienti'].unique()
    klientet = st.sidebar.multiselect("Zgjidh Klientët:", options=sorted([str(x) for x in k_list if x != 'nan']))

    # FILTRIMI
    dff = df.copy()
    if agj_sel != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agj_sel]
    if klientet:
        dff = dff[dff['Klienti'].isin(klientet)]

    # AGREGIMI (Përdorim observed=True për të mos krijuar matrica bosh në RAM)
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli'], observed=True).agg({'kg': 'sum'}).reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Llogaritja e planit (bazuar në 12 muaj mesatare)
    gp['Plani_KG'] = (gp['kg'] / 12 * (1 + rritja/100)).round(1)
    gp['Vlera_Lekë'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(0)

    # SHFAQJA
    st.title("📊 Plani i Shitjeve")
    c1, c2, c3 = st.columns(3)
    c1.metric("KG Totale", f"{gp['Plani_KG'].sum():,.0f}")
    c2.metric("Vlera Totale", f"{gp['Vlera_Lekë'].sum():,.0f} L")
    c3.metric("Nr. Klientëve", len(gp['Klienti'].unique()))

    st.divider()
    st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Lekë']], use_container_width=True)