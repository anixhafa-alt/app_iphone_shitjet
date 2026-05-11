import streamlit as st
import pandas as pd

# 1. Konfigurimi i faqes për iPhone (Mobile Friendly)
st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

@st.cache_data
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Kolonat sipas specifikimeve të tua
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        # Pastrimi i emrave të kolonave
        df.columns = df.columns.str.strip().str.replace('"', '')
        # Konvertimi i datës nga formati Excel
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        # Llogarisim çmimin për çdo rresht (VleraRresht / kg)
        df['Cmimi_Rreshtit'] = df['VleraRresht'] / df['kg'].replace(0, 1)
        return df
    except Exception as e:
        st.error(f"Gabim gjatë ngarkimit: {e}")
        return None

df = load_data()

if df is not None:
    # --- LOGJIKA E ÇMIMIT TË FUNDIT (Pika 7) ---
    # Gjejmë çmimin e fundit të shitjes për çdo artikull në të gjithë historikun
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')
    last_prices = last_prices[['Artikulli', 'Cmimi_Rreshtit']].rename(columns={'Cmimi_Rreshtit': 'Cmimi_Fundit'})

    # --- SIDEBAR (Filtrat dhe Parametrat) ---
    st.sidebar.header("⚙️ Parametrat e Planit")
    
    # Zgjedhja e periudhës referente për KG
    min_d = df['Data'].min().date()
    max_d = df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente për KG:", value=(min_d, max_d))
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_d, max_d

    # Kuti për rritjen e planit
    rritja_perqindje = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # Filtri i Agjentit
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti_select = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    # FILTRI I KLIENTËVE (Drop-filter i rregulluar)
    if agjenti_select != "Të gjithë":
        temp_klient_list = df[df['ForcaShitese'].astype(str) == agjenti_select]['Klienti'].unique()
    else:
        temp_klient_list = df['Klienti'].unique()
        
    # Sigurohemi që lista e klientëve nuk ka NaN dhe është e renditur
    klient_list = sorted([str(x) for x in temp_klient_list if pd.notna(x)])
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin (Search):", options=klient_list)

    # --- FILTRIMI I TË DHËNAVE ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti_select != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti_select]
    if klientet_selected:
        dff = dff[dff['Klienti'].isin(klientet_selected)]

    # Llogaritja e muajve të periudhës referente
    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- AGREGIMI DHE PLANIFIKIMI ---
    # Grupojmë KG-të për periudhën referente
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({'kg': 'sum'}).reset_index()
    
    # Bashkojmë me çmimet e fundit
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Llogaritjet e planit të ri
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja_perqindje/100)).round(1)
    gp['Vlera_Planifikuar'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(2)

    # --- LLOGARITJET PËR KOKËN (METRICS) ---
    total_plani_kg = gp['Plani_KG'].sum()
    total_plani_vlera = gp['Vlera_Planifikuar'].sum()
    cmimi_mesatar_planit = total_plani_vlera / total_plani_kg if total_plani_kg > 0 else 0

    # --- SHFAQJA NË EKRAN ---
    st.title("📊 Sistemi i Planifikimit")
    
    # Metricat në kokë (Pika 1 & 7)
    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG Totale", f"{total_plani_kg:,.0f}")
    c2.metric("Cmimi Mesatar Planit", f"{cmimi_mesatar_planit:,.2f} L/kg")
    c3.metric("Vlera Totale e Planit", f"{total_plani_vlera:,.0f} Lekë")

    st.divider()

    # Shfaqja e rezultateve
    if klientet_selected:
        st.subheader(f"📍 Plani i Detajuar për Klientët e zgjedhur")
        # Shfaqim të dhënat e detajuara
        st.dataframe(
            gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera_Planifikuar']], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        # Pamja me Tabs nëse nuk ka klient specifik të zgjedhur
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

    # Butoni për shkarkim
    csv = gp.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Shkarko Planin e Plotë (CSV)", csv, "plani_shitjeve.csv", "text/csv")