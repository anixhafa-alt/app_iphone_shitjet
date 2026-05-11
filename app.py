import streamlit as st
import pandas as pd

# 1. Konfigurimi i faqes
st.set_page_config(page_title="Sistemi i Planifikimit", layout="wide")

@st.cache_data(ttl=600)
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip().str.replace('"', '')
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        # Llogarisim çmimin (float32 për të kursyer RAM)
        df['Cmimi'] = (df['VleraRresht'] / df['kg'].replace(0, 1)).astype('float32')
        df.drop(columns=['VleraRresht'], inplace=True)
        
        # Optimizimi i kolonave në kategori
        for c in ['ForcaShitese', 'Klienti', 'kat', 'Artikulli']:
            df[c] = df[c].astype(str).astype('category')
            
        return df
    except Exception as e:
        st.error(f"Gabim gjatë ngarkimit: {e}")
        return None

df = load_data()

if df is not None:
    # --- LOGJIKA E ÇMIMIT TË FUNDIT ---
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi']]
    last_prices.rename(columns={'Cmimi': 'Cmimi_Fundit'}, inplace=True)

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Kontrolli")
    
    min_d, max_d = df['Data'].min().date(), df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
    start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
    
    rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # Filtra dinamikë
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x != 'nan'])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    if agj_sel != "Të gjithë":
        k_list = df[df['ForcaShitese'].astype(str) == agj_sel]['Klienti'].unique()
    else:
        k_list = df['Klienti'].unique()
    
    klient_list = sorted([str(x) for x in k_list if x != 'nan'])
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin (Search):", options=klient_list)

    # --- FILTRIMI ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agj_sel != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agj_sel]
    if klientet_selected:
        dff = dff[dff['Klienti'].astype(str).isin(klientet_selected)]

    # Llogaritja e muajve
    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- AGREGIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli'], observed=True)['kg'].sum().reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja/100)).round(1)
    gp['Vlera_Planifikuar'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(0)

    # --- TITULLI DINAMIK ---
    muajt_sq = {
        "January": "Janar", "February": "Shkurt", "March": "Mars",
        "April": "Prill", "May": "Maj", "June": "Qershor",
        "July": "Korrik", "August": "Gusht", "September": "Shtator",
        "October": "Tetor", "November": "Nëntor", "December": "Dhjetor"
    }
    next_month_dt = (pd.to_datetime(end_date) + pd.DateOffset(months=1))
    muaji_sq = muajt_sq.get(next_month_dt.strftime('%B'), next_month_dt.strftime('%B'))
    viti = next_month_dt.strftime('%Y')

    st.title(f"🎯 Plani: {muaji_sq} {viti}")
    st.caption("ℹ️ Llogaritjet bazohen në *çmimet e fundit* të shitjes.")

    # Metrics
    t_kg = gp['Plani_KG'].sum()
    t_v = gp['Vlera_Planifikuar'].sum()
    c_m = t_v / t_kg if t_kg > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG Totale", f"{t_kg:,.0f}")
    c2.metric("Cmimi Mesatar Planit", f"{c_m:,.2f} L/kg")
    c3.metric("Vlera Totale e Planit", f"{t_v:,.0f} L")

    st.divider()

    # --- FUNKSION PËR SHTIMIN E ÇMIMIT NË GRUPIME ---
    def llogarit_cmimin_grup(dataframe):
        # Cmimi mesatar i ponderuar = Vlera Totale / KG Totale
        dataframe['Cmimi_Mes'] = (dataframe['Vlera_Planifikuar'] / dataframe['Plani_KG']).round(2)
        return dataframe

    # --- SHFAQJA ---
    if klientet_selected:
        st.subheader(f"📍 Detajet për klientët")
        # Te detajet, Cmimi_Fundit është ai që kërkove (Vlera/Plani_KG)
        st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Planifikuar']], 
                     use_container_width=True, hide_index=True)
    else:
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        
        with t1:
            kat_v = gp.groupby('kat', observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            kat_v = llogarit_cmimin_grup(kat_v)
            st.dataframe(kat_v[['kat', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True)
            
        with t2:
            agj_v = gp.groupby('ForcaShitese', observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            agj_v = llogarit_cmimin_grup(agj_v)
            st.dataframe(agj_v[['ForcaShitese', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True)
            
        with t3:
            klient_v = gp.groupby(['Klienti', 'ForcaShitese'], observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            klient_v = llogarit_cmimin_grup(klient_v)
            st.dataframe(klient_v[['Klienti', 'ForcaShitese', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True)