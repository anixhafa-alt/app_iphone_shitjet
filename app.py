import streamlit as st
import pandas as pd

# 1. Konfigurimi
st.set_page_config(page_title="Sistemi i Shitjeve", layout="wide")

# Funksion i optimizuar deri në ekstrem
@st.cache_data(ttl=300, max_entries=1) # Fshin memorjen çdo 5 minuta automatikisht
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        # Lexojmë skedarin
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # Konvertojmë në formate "të lehta"
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        # Llogarisim çmimin dhe fshijmë kolonën VleraRresht menjëherë
        df['Cmimi'] = (df['VleraRresht'] / df['kg'].replace(0, 1)).astype('float32')
        df.drop(columns=['VleraRresht'], inplace=True)
        
        # Kthejmë tekstet në kategori për të kursyer 90% të RAM
        for c in ['ForcaShitese', 'Klienti', 'kat']:
            df[c] = df[c].astype('category')
            
        return df
    except Exception as e:
        st.error(f"Gabim: {e}")
        return None

df = load_data()

if df is not None:
    # Llogarisim çmimet e fundit në një tabelë shumë të vogël
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi']]
    last_prices.columns = ['Artikulli', 'Cmimi_Fundit']

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Kontrolli")
    rritja = st.sidebar.number_input("Rritja (%)", value=10)
    
    # Filtra të shpejtë
    agj_list = sorted(df['ForcaShitese'].dropna().unique().tolist())
    agj_sel = st.sidebar.selectbox("Agjenti:", ["Të gjithë"] + agj_list)
    
    # Filtri i klientëve
    if agj_sel != "Të gjithë":
        k_list = df[df['ForcaShitese'] == agj_sel]['Klienti'].dropna().unique().tolist()
    else:
        k_list = df['Klienti'].dropna().unique().tolist()
    
    klientet = st.sidebar.multiselect("Zgjidh Klientin:", options=sorted([str(x) for x in k_list]))

    # --- FILTRIMI ---
    # Përdorim dff vetëm me kolonat që duhen për tabelën finale
    dff = df[['ForcaShitese', 'Klienti', 'kat', 'Artikulli', 'kg']].copy()
    if agj_sel != "Të gjithë":
        dff = dff[dff['ForcaShitese'] == agj_sel]
    if klientet:
        dff = dff[dff['Klienti'].isin(klientet)]

    # --- AGREGIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli'], observed=True)['kg'].sum().reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Llogaritja e planit (bazuar në 12 muaj)
    gp['Plani_KG'] = (gp['kg'] / 12 * (1 + rritja/100)).round(1)
    gp['Vlera_Lekë'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(0)

    # --- METRICS ---
    st.title("📊 Plani i Shitjeve")
    t_kg = gp['Plani_KG'].sum()
    t_v = gp['Vlera_Lekë'].sum()
    c_m = t_v / t_kg if t_kg > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG", f"{t_kg:,.0f}")
    c2.metric("Cmimi Mesatar", f"{c_m:,.2f}")
    c3.metric("Vlera Totale", f"{t_v:,.0f} L")

    st.divider()
    # Shfaqim vetëm rreshtat që kanë KG (për të kursyer hapësirë në iPhone)
    final_table = gp[gp['Plani_KG'] > 0][['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Lekë']]
    st.dataframe(final_table, use_container_width=True, hide_index=True)