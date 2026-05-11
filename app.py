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
        
        # Llogarisim çmimin (float32 për kursim RAM)
        df['Cmimi'] = (df['VleraRresht'] / df['kg'].replace(0, 1)).astype('float32')
        df.drop(columns=['VleraRresht'], inplace=True)
        
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

    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x != 'nan'])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    k_list = df[df['ForcaShitese'].astype(str) == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df['Klienti'].unique()
    klient_list = sorted([str(x) for x in k_list if x != 'nan'])
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin (Search):", options=klient_list)

    # --- FILTRIMI ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()
    if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'].astype(str) == agj_sel]
    if klientet_selected: dff = dff[dff['Klienti'].astype(str).isin(klientet_selected)]

    # Llogaritja e muajve
    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- AGREGIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli'], observed=True)['kg'].sum().reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja/100))
    gp['Vlera_Planifikuar'] = (gp['Plani_KG'] * gp['Cmimi_Fundit'])

    # --- TITULLI ---
    muajt_sq = {"January": "Janar", "February": "Shkurt", "March": "Mars", "April": "Prill", "May": "Maj", "June": "Qershor", "July": "Korrik", "August": "Gusht", "September": "Shtator", "October": "Tetor", "November": "Nëntor", "December": "Dhjetor"}
    next_month_dt = (pd.to_datetime(end_date) + pd.DateOffset(months=1))
    st.title(f"🎯 Plani: {muajt_sq.get(next_month_dt.strftime('%B'))} {next_month_dt.strftime('%Y')}")
    st.caption("ℹ️ Çmimet bazohen në shitjen e fundit. Formatimi: Numra të plotë me ndarje mijëshe.")

    # Metrics
    t_kg, t_v = gp['Plani_KG'].sum(), gp['Vlera_Planifikuar'].sum()
    c_m = t_v / t_kg if t_kg > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG Totale", f"{t_kg:,.0f}")
    c2.metric("Cmimi Mesatar", f"{c_m:,.1f} L/kg")
    c3.metric("Vlera Totale", f"{t_v:,.0f} L")

    # --- KONFIGURIMI I KOLONAVE (FORMATIMI) ---
    formati_kolonave = {
        "Cmimi_Fundit": st.column_config.NumberColumn("Cmimi", format="%.1f L"),
        "Cmimi_Mes": st.column_config.NumberColumn("Cmimi Mes.", format="%.1f L"),
        "Plani_KG": st.column_config.NumberColumn("Plani KG", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d"),
    }

    st.divider()

    if klientet_selected:
        st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Planifikuar']], 
                     use_container_width=True, hide_index=True, column_config=formati_kolonave)
    else:
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        
        with t1:
            df_k = gp.groupby('kat', observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            df_k['Cmimi_Mes'] = df_k['Vlera_Planifikuar'] / df_k['Plani_KG']
            st.dataframe(df_k[['kat', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=formati_kolonave)
            
        with t2:
            df_a = gp.groupby('ForcaShitese', observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            df_a['Cmimi_Mes'] = df_a['Vlera_Planifikuar'] / df_a['Plani_KG']
            st.dataframe(df_a[['ForcaShitese', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=formati_kolonave)
            
        with t3:
            df_kl = gp.groupby(['Klienti', 'ForcaShitese'], observed=True).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            df_kl['Cmimi_Mes'] = df_kl['Vlera_Planifikuar'] / df_kl['Plani_KG']
            st.dataframe(df_kl[['Klienti', 'ForcaShitese', 'Cmimi_Mes', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=formati_kolonave)