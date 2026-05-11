import streamlit as st
import pandas as pd
from datetime import datetime
import base64

# --- KONFIGURIMI ---
st.set_page_config(page_title="DEKA Analytics", layout="wide")

# Fjalori për Muajt Shqip
muajt_shqip = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
}

# --- SISTEMI I SIGURISE ---
if "password_correct" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>Hyrja në Sistem</h2>", unsafe_allow_html=True)
    pw = st.text_input("Fjalëkalimi:", type="password")
    if pw == "admin123":
        st.session_state["password_correct"] = True
        st.rerun()
    st.stop()

# --- NAVIGIMI (Butonat e Faqeve) ---
st.sidebar.title("🧭 Menuja Kryesore")
page = st.sidebar.radio("Zgjidh Modulin:", ["Historiku", "Planifikimi", "Realizimi", "Mundësitë"])

# --- NGARKIMI I TE DHENAVE (Shared Cache) ---
@st.cache_data(ttl=3600)
def load_all_data():
    try:
        conn = st.connection("sql", type="sql")
        # Marrim te gjitha te dhenat per te gjitha vitet
        df_sql = conn.query("SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView")
        df_sql.columns = df_sql.columns.str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data'])
        
        # Mapping me Excel
        df_map = pd.read_excel('produkte+.xlsx', sheet_name='produktet')
        df_map.columns = df_map.columns.str.strip()
        df_map = df_map[['KODI', 'KATEG.', 'KG/SKU']].copy()
        
        df = pd.merge(df_sql, df_map, left_on='KodiArt', right_on='KODI', how='left')
        df['kg'] = df['Sasia'] * df['KG/SKU'].fillna(0)
        df.rename(columns={'KATEG.': 'kat'}, inplace=True)
        df['kat'] = df['kat'].fillna('ETJ')
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Gabim teknik: {e}")
        return None

df_raw = load_all_data()

# ---------------------------------------------------------
# MODULI: PLANIFIKIMI
# ---------------------------------------------------------
if page == "Planifikimi":
    st.title(f"📊 Planifikimi - {muajt_shqip[datetime.now().month]} {datetime.now().year}")
    
    if df_raw is not None:
        # 1. Kalkulimi i Çmimit të Fundit (Duke perjashtuar muajin korrent)
        sot = datetime.now()
        mask_past = (df_raw['Data'].dt.year < sot.year) | ((df_raw['Data'].dt.year == sot.year) & (df_raw['Data'].dt.month < sot.month))
        df_past = df_raw[mask_past].copy()
        
        df_past['Cmimi_Rresht'] = df_past['Vlera_Historike'] / df_past['kg'].replace(0, 1)
        last_prices = df_past.sort_values('Data').drop_duplicates('KodiArt', keep='last')[['KodiArt', 'Cmimi_Rresht']]
        last_prices.rename(columns={'Cmimi_Rresht': 'Cmimi_Fundit_Artikulli'}, inplace=True)

        # 2. Sidebar Filtra
        st.sidebar.subheader("Filtrat e Planit")
        rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)
        
        # Filtri Data (Periudha Referente)
        min_d, max_d = df_raw['Data'].min().date(), df_raw['Data'].max().date()
        date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
        start_d, end_d = date_range if len(date_range)==2 else (min_d, max_d)
        
        # Filtra tjerë
        agj_list = sorted(df_raw['ForcaShitese'].unique().tolist())
        agj_sel = st.sidebar.selectbox("Agjenti:", ["Të gjithë"] + agj_list)
        
        # Filtri Klienti (Rikthyer)
        k_list = df_raw[df_raw['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df_raw['Klienti'].unique()
        klientet_sel = st.sidebar.multiselect("Zgjidh Klientët:", sorted(list(k_list)))

        # 3. Procesimi
        mask = (df_raw['Data'].dt.date >= start_d) & (df_raw['Data'].dt.date <= end_d)
        dff = df_raw.loc[mask].copy()
        if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]
        if klientet_sel: dff = dff[dff['Klienti'].isin(klientet_sel)]

        n_months = max(1, (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month))

        gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'KodiArt', 'Artikulli']).agg({'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
        gp['Cmimi_Mes_Periudhes'] = gp['Vlera_Historike'] / gp['kg'].replace(0, 1)
        gp = gp.merge(last_prices, on='KodiArt', how='left')
        
        gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
        gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli'].fillna(gp['Cmimi_Mes_Periudhes'])

        # 4. METRIKAT (Rikthyer Çmimet)
        t_kg = gp['Plani_KG'].sum()
        t_vl = gp['Vlera_Planifikuar'].sum()
        cm_fundit_avg = gp['Cmimi_Fundit_Artikulli'].mean()
        cm_periudhe_avg = gp['Cmimi_Mes_Periudhes'].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KG Plan Totale", f"{t_kg:,.0f}")
        m2.metric("Vlera Plan Totale", f"{t_vl:,.0f} L")
        m3.metric("Çmimi Fundit (Avg)", f"{cm_fundit_avg:,.1f} L")
        m4.metric("Çmimi Periudhës (Avg)", f"{cm_periudhe_avg:,.1f} L")

        st.divider()

        # 5. TABELA (Me kolonën e Çmimit të Periudhës)
        st.subheader("Detajet e Planifikimit")
        st.dataframe(
            gp[['ForcaShitese', 'Klienti', 'Artikulli', 'kat', 'Cmimi_Mes_Periudhes', 'Cmimi_Fundit_Artikulli', 'Plani_KG', 'Vlera_Planifikuar']],
            column_config={
                "Cmimi_Mes_Periudhes": st.column_config.NumberColumn("Çmim Periudhe", format="%.1f L"),
                "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn("Çmim i Fundit", format="%.1f L"),
                "Plani_KG": st.column_config.NumberColumn("KG Plan", format="%d"),
                "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Plan", format="%d L")
            },
            hide_index=True, use_container_width=True
        )

# ---------------------------------------------------------
# MODULI: REALIZIMI (Struktura fillestare)
# ---------------------------------------------------------
elif page == "Realizimi":
    st.title("📈 Realizimi i Planit (Live)")
    st.warning("Ky modul krahason Shitjet e muajit korrent me Planin e gjeneruar.")
    # Këtu do të vendosim logjikën e krahasimit muajin tjetër

elif page == "Historiku":
    st.title("📚 Historiku i Shitjeve")
    st.info("Këtu mund të analizoni shitjet ndër vite.")

elif page == "Mundësitë":
    st.title("🔍 Mundësitë & Analiza e Klientit")
    st.info("Analiza e klientëve aktivë dhe atyre në rrezik.")