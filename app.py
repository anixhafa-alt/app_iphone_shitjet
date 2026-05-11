import streamlit as st
import pandas as pd
from datetime import datetime
import base64

# --- KONFIGURIMI I FAQES ---
st.set_page_config(page_title="DEKA Analytics - SQL Real-Time", layout="wide")

# Fjalori për Muajt Shqip për titullin
muajt_shqip = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
}

# --- SISTEMI I SIGURISE ---
if "password_correct" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>Hyrja në Sistem</h2>", unsafe_allow_html=True)
    pw = st.text_input("Fjalëkalimi:", type="password")
    if pw == "admin123": # Mund ta ndryshosh kete
        st.session_state["password_correct"] = True
        st.rerun()
    st.stop()

# --- NAVIGIMI (MENUJA ANASH) ---
st.sidebar.title("🧭 Menuja Kryesore")
page = st.sidebar.radio("Zgjidh Modulin:", ["Historiku", "Planifikimi", "Realizimi", "Mundësitë"])

# --- NGARKIMI I TE DHENAVE (SHARED CACHE) ---
@st.cache_data(ttl=3600)
def load_all_data():
    try:
        # Lidhja me SQL
        conn = st.connection("sql", type="sql")
        df_sql = conn.query("SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView")
        df_sql.columns = df_sql.columns.str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data'])
        
        # Leximi i Excel me kolonën e saktë 'KATEG.'
        df_map = pd.read_excel('produkte+.xlsx', sheet_name='produktet')
        df_map.columns = df_map.columns.str.strip()
        
        # Përdorim 'KATEG.' sipas kërkesës tënde
        df_map = df_map[['KODI', 'KATEG.', 'KG/SKU']].copy()
        df_map['KODI'] = df_map['KODI'].astype(str).str.strip()
        
        # Merge SQL + Excel
        df = pd.merge(df_sql, df_map, left_on='KodiArt', right_on='KODI', how='left')
        
        # Llogaritjet bazë
        df['kg'] = df['Sasia'] * df['KG/SKU'].fillna(0)
        df.rename(columns={'KATEG.': 'kat'}, inplace=True)
        df['kat'] = df['kat'].fillna('ETJ')
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Gabim gjatë ngarkimit: {e}")
        return None

df_raw = load_all_data()

# =========================================================
# MODULI 1: PLANIFIKIMI
# =========================================================
if page == "Planifikimi":
    sot = datetime.now()
    st.title(f"📊 Planifikimi - {muajt_shqip[sot.month]} {sot.year}")
    
    if df_raw is not None:
        # 1. ÇMIMI I FUNDIT (Duke përjashtuar muajin korrent)
        mask_past = (df_raw['Data'].dt.year < sot.year) | ((df_raw['Data'].dt.year == sot.year) & (df_raw['Data'].dt.month < sot.month))
        df_past = df_raw[mask_past].copy()
        
        df_past['Cmimi_Rresht'] = df_past['Vlera_Historike'] / df_past['kg'].replace(0, 1)
        last_prices = df_past.sort_values('Data').drop_duplicates('KodiArt', keep='last')[['KodiArt', 'Cmimi_Rresht']]
        last_prices.rename(columns={'Cmimi_Rresht': 'Cmimi_Fundit_Artikulli'}, inplace=True)

        # 2. FILTRAT NE SIDEBAR
        st.sidebar.subheader("⚙️ Parametrat e Planit")
        rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)
        
        min_d, max_d = df_raw['Data'].min().date(), df_raw['Data'].max().date()
        date_range = st.sidebar.date_input("Periudha referente (Historiku):", value=(min_d, max_d))
        start_d, end_d = date_range if len(date_range)==2 else (min_d, max_d)
        
        agj_list = sorted(df_raw['ForcaShitese'].unique().tolist())
        agj_sel = st.sidebar.selectbox("Zgjidh Agjentin:", ["Të gjithë"] + agj_list)
        
        # Filtri i Klientit (Multiselect)
        k_list = df_raw[df_raw['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df_raw['Klienti'].unique()
        klientet_sel = st.sidebar.multiselect("Filtro Klientët:", sorted(list(k_list)))

        # 3. PROCESIMI I TE DHENAVE
        mask = (df_raw['Data'].dt.date >= start_d) & (df_raw['Data'].dt.date <= end_d)
        dff = df_raw.loc[mask].copy()
        if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]
        if klientet_sel: dff = dff[dff['Klienti'].isin(klientet_sel)]

        n_months = max(1, (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month))

        # Agregimi
        gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'KodiArt', 'Artikulli']).agg({'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
        gp['Cmimi_Mes_Periudhes'] = gp['Vlera_Historike'] / gp['kg'].replace(0, 1)
        gp = gp.merge(last_prices, on='KodiArt', how='left')
        
        # Llogaritja e Planit
        gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
        # Nese nuk ka cmim fundit (artikull i ri), perdor cmimin e periudhes
        gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli'].fillna(gp['Cmimi_Mes_Periudhes'])

        # 4. METRIKAT KRYESORE
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KG Plan Totale", f"{gp['Plani_KG'].sum():,.0f}")
        m2.metric("Vlera Plan Totale", f"{gp['Vlera_Planifikuar'].sum():,.0f} L")
        m3.metric("Çmimi Fundit (Avg)", f"{gp['Cmimi_Fundit_Artikulli'].mean():,.1f} L")
        m4.metric("Çmimi Periudhës (Avg)", f"{gp['Cmimi_Mes_Periudhes'].mean():,.1f} L")

        st.divider()

        # 5. TABELA E PLANIT
        st.subheader("📋 Detajet e Planit")
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

        # 6. EKSPORTI HTML
        def generate_html(dataframe):
            html = "<html><body><h2>Raporti i Planit</h2><table border='1'><tr><th>Agjenti</th><th>Kategoria</th><th>KG Plan</th><th>Vlera Plan</th></tr>"
            agj_sum = dataframe.groupby(['ForcaShitese', 'kat']).agg({'Plani_KG':'sum', 'Vlera_Planifikuar':'sum'}).reset_index()
            for _, row in agj_sum.iterrows():
                html += f"<tr><td>{row['ForcaShitese']}</td><td>{row['kat']}</td><td>{row['Plani_KG']:,.0f}</td><td>{row['Vlera_Planifikuar']:,.0f}</td></tr>"
            html += "</table></body></html>"
            return html

        if st.sidebar.button("Gjenero Raportin HTML"):
            b64 = base64.b64encode(generate_html(gp).encode()).decode()
            st.sidebar.markdown(f'<a href="data:text/html;base64,{b64}" download="plani.html" style="color:white; background:blue; padding:10px; border-radius:5px; text-decoration:none;">Shkarko Raportin</a>', unsafe_allow_html=True)

# =========================================================
# MODULET TJERA (STARTUP STRUCTURE)
# =========================================================
elif page == "Historiku":
    st.title("📚 Historiku i Shitjeve")
    st.info("Këtu do të shfaqen trendet e shitjeve ndër vite (Work in progress).")

elif page == "Realizimi":
    st.title("📈 Realizimi Live")
    st.success(f"Muaji korrent: {muajt_shqip[datetime.now().month]}. Këtu do të krahasojmë shitjet live nga SQL me planin.")

elif page == "Mundësitë":
    st.title("🔍 Mundësitë & Klientët")
    st.info("Analiza e klientëve aktive dhe vlerësimi i riskut.")