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
        df['ForcaShitese'] = df['ForcaShitese'].astype(str).str.strip()
        df['Klienti'] = df['Klienti'].astype(str).str.strip()
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        # Ruajmë vlerën për llogaritje mesatareje më vonë
        df['Vlera_Historike'] = df['VleraRresht'].astype('float32')
        df.drop(columns=['VleraRresht'], inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Gabim gjatë ngarkimit: {e}")
        return None

df = load_data()

if df is not None:
    data_fundit = df['Data'].max().strftime('%d/%m/%Y')

    # --- LOGJIKA E ÇMIMIT TË FUNDIT (Nga e gjithë historia) ---
    df['Cmimi_Rresht'] = (df['Vlera_Historike'] / df['kg'].replace(0, 1))
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi_Rresht']]
    last_prices.rename(columns={'Cmimi_Rresht': 'Cmimi_Fundit_Artikulli'}, inplace=True)

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Kontrolli")
    min_d, max_d = df['Data'].min().date(), df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
    start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
    
    rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)

    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x not in ['nan', 'None']])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    k_list = df[df['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df['Klienti'].unique()
    klient_list = sorted([str(x) for x in k_list if x not in ['nan', 'None']])
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin (Search):", options=klient_list)

    # --- FILTRIMI ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()
    if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]
    if klientet_selected: dff = dff[dff['Klienti'].isin(klientet_selected)]

    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    # --- AGREGIMI (Shtohet llogaritja e çmimit mesatar të periudhës) ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({
        'kg': 'sum',
        'Vlera_Historike': 'sum'
    }).reset_index()
    
    # Llogaritja e çmimit mesatar vetëm për periudhën e zgjedhur
    gp['Cmimi_Mes_Periudhes'] = (gp['Vlera_Historike'] / gp['kg'].replace(0, 1))
    
    # Lidhim me çmimin e fundit (nga e gjithë historia)
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Llogaritjet e planit (Bazohen te Cmimi i Fundit)
    gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
    gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli']

    # --- TITULLI ---
    muajt_sq = {"January": "Janar", "February": "Shkurt", "March": "Mars", "April": "Prill", "May": "Maj", "June": "Qershor", "July": "Korrik", "August": "Gusht", "September": "Shtator", "October": "Tetor", "November": "Nëntor", "December": "Dhjetor"}
    next_month_dt = (pd.to_datetime(end_date) + pd.DateOffset(months=1))
    st.title(f"🎯 Plani: {muajt_sq.get(next_month_dt.strftime('%B'))} {next_month_dt.strftime('%Y')}")
    st.info(f"📅 Update i fundit: **{data_fundit}** | Planifikimi bazohet te **Çmimi i Fundit**.")

    # Metrics
    t_kg, t_v = gp['Plani_KG'].sum(), gp['Vlera_Planifikuar'].sum()
    c_m = t_v / t_kg if t_kg > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG Totale", f"{t_kg:,.0f}")
    c2.metric("Çmimi Fundit Mes.", f"{c_m:,.1f} L/kg")
    c3.metric("Vlera Totale", f"{t_v:,.0f} L")

    # --- KONFIGURIMI I KOLONAVE ---
    config_kolonave = {
        "Cmimi_Mes_Periudhes": st.column_config.NumberColumn("Çmimi Mes. Periudhës", format="%.1f L"),
        "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn("Çmimi i Fundit", format="%.1f L"),
        "Cmimi_Mes_Grup": st.column_config.NumberColumn("Çmimi Mes. Grup", format="%.1f L"),
        "Plani_KG": st.column_config.NumberColumn("Plani KG", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d")
    }

    st.divider()

    if klientet_selected:
        st.subheader("📍 Detajet Artikujve (Krahasimi i Çmimeve)")
        st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Mes_Periudhes', 'Cmimi_Fundit_Artikulli', 'Plani_KG', 'Vlera_Planifikuar']], 
                     use_container_width=True, hide_index=True, column_config=config_kolonave)
    else:
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        with t1:
            df_k = gp.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_k['Cmimi_Mes_Periudhes'] = df_k['Vlera_Historike'] / df_k['kg'].replace(0, 1)
            df_k['Cmimi_Mes_Grup'] = df_k['Vlera_Planifikuar'] / df_k['Plani_KG'].replace(0, 1)
            st.dataframe(df_k[['kat', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=config_kolonave)
        with t2:
            df_a = gp.groupby('ForcaShitese').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_a['Cmimi_Mes_Periudhes'] = df_a['Vlera_Historike'] / df_a['kg'].replace(0, 1)
            df_a['Cmimi_Mes_Grup'] = df_a['Vlera_Planifikuar'] / df_a['Plani_KG'].replace(0, 1)
            st.dataframe(df_a[['ForcaShitese', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=config_kolonave)
        with t3:
            df_kl = gp.groupby(['Klienti', 'ForcaShitese']).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_kl['Cmimi_Mes_Periudhes'] = df_kl['Vlera_Historike'] / df_kl['kg'].replace(0, 1)
            df_kl['Cmimi_Mes_Grup'] = df_kl['Vlera_Planifikuar'] / df_kl['Plani_KG'].replace(0, 1)
            st.dataframe(df_kl[['Klienti', 'ForcaShitese', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         use_container_width=True, hide_index=True, column_config=config_kolonave)