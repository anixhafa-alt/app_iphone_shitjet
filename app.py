import streamlit as st
import pandas as pd

st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

# Optimizo leximin për të shmangur Memory Error (1011)
@st.cache_data(ttl=3600) # Liron memorjen çdo 1 orë
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Lexojmë VETËM kolonat që përdorim në llogaritje
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        # Përdorim dtype për të kursyer memorje
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        
        # Pastrojmë emrat e kolonave
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # Konvertojmë në formate që zënë pak hapësirë
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        df['ForcaShitese'] = df['ForcaShitese'].astype('category')
        df['kat'] = df['kat'].astype('category')
        
        # Llogarisim çmimin menjëherë
        df['Cmimi_Rreshtit'] = df['VleraRresht'] / df['kg'].replace(0, 1)
        
        # Fshijmë kolonën VleraRresht pasi nuk na duhet më (kursen RAM)
        df.drop(columns=['VleraRresht'], inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Gabim në ngarkim: {e}")
        return None

df = load_data()

if df is not None:
    # Gjejmë çmimin e fundit (logjikë e shpejtë)
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')
    last_prices = last_prices[['Artikulli', 'Cmimi_Rreshtit']].rename(columns={'Cmimi_Rreshtit': 'Cmimi_Fundit'})

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Parametrat")
    
    min_d, max_d = df['Data'].min().date(), df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
    
    start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
    rritja = st.sidebar.number_input("Rritja (%)", value=10)

    # Filtrat e blinduar kundër TypeError
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti = st.sidebar.selectbox("Agjenti:", ["Të gjithë"] + agj_list)
    
    temp_klient_list = df[df['ForcaShitese'].astype(str) == agjenti]['Klienti'].unique() if agjenti != "Të gjithë" else df['Klienti'].unique()
    klient_list = sorted([str(x) for x in temp_klient_list if pd.notna(x)])
    klientet = st.sidebar.multiselect("Zgjidh Klientin:", options=klient_list)

    # --- FILTRIMI DHE LLOGARITJA ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti]
    if klientet:
        dff = dff[dff['Klienti'].astype(str).isin(klientet)]

    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    # Agregimi
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli'], observed=True).agg({'kg': 'sum'}).reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja/100)).round(1)
    gp['Vlera_P'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(0)

    # Metricat
    t_kg = gp['Plani_KG'].sum()
    t_v = gp['Vlera_P'].sum()
    c_m = t_v / t_kg if t_kg > 0 else 0

    st.title("📊 Plani i Shitjeve")
    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG", f"{t_kg:,.0f}")
    c2.metric("Cmimi Mesatar", f"{c_m:,.2f}")
    c3.metric("Vlera Totale", f"{t_v:,.0f} L")

    # Tabs
    st.divider()
    t1, t2, t3 = st.tabs(["Kategoritë", "Agjentët", "Klientët"])
    with t1:
        st.dataframe(gp.groupby('kat', observed=True).agg({'Plani_KG': 'sum', 'Vlera_P': 'sum'}).reset_index(), use_container_width=True)
    with t2:
        st.dataframe(gp.groupby('ForcaShitese', observed=True).agg({'Plani_KG': 'sum', 'Vlera_P': 'sum'}).reset_index(), use_container_width=True)
    with t3:
        st.dataframe(gp.groupby(['Klienti', 'ForcaShitese'], observed=True).agg({'Plani_KG': 'sum', 'Vlera_P': 'sum'}).reset_index(), use_container_width=True)