import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import sqlalchemy

# 1. Konfigurimi i faqes
st.set_page_config(page_title="Sistemi i Planifikimit - DEKA SQL", layout="wide")

# Fjalori për Muajt Shqip
muajt_sq = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nentor", 12: "Dhjetor"
}

# --- SISTEMI I SIGURISE (LOGIN) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>Hyrja në Sistem</h2>", unsafe_allow_html=True)
        st.text_input("Shkruaj fjalëkalimin:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Fjalëkalim i gabuar!", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

def password_entered():
    if st.session_state["password"] == "deka2024":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

# --- NGARKIMI I TE DHENAVE (VERSIONI I KORRIGJUAR) ---
@st.cache_data(ttl=600)
def load_all_data():
    try:
        # A. Lidhja me SQL
        # Shenim: Perdoret Driver 17 sepse eshte me i perhapuri ne Streamlit Cloud/Linux
        connection_string = (
            "mssql+pyodbc://DEKAReportsUser:DekaR3p0rt$V1ew!@Deka.ivaelektronik.com:4433/SADN?"
            "driver=ODBC+Driver+17+for+SQL+Server&"
            "TrustServerCertificate=yes"
        )
        conn = st.connection("sql", type="sql", url=connection_string)

        df_sql = conn.query("SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView")
        df_sql.columns = df_sql.columns.str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data'])
        
        # B. Leximi i Excel-it (Sheet: produktet)
        df_link = pd.read_excel('prod.xlsx', sheet_name='produktet', engine='openpyxl')
        df_link.columns = df_link.columns.astype(str).str.strip().str.upper()
        
        # C. Leximi i Excel-it (Sheet: kat_prod)
        df_map = pd.read_excel('prod.xlsx', sheet_name='kat_prod', engine='openpyxl')
        df_map.columns = df_map.columns.astype(str).str.strip().str.upper()

        # Kontroll automatik per emrat e kolonave te kategorive
        if 'EMER KAT' not in df_map.columns and 'EMRI KAT' in df_map.columns:
            df_map = df_map.rename(columns={'EMRI KAT': 'EMER KAT'})

        # D. BASHKIMI (Merge)
        df_sql['KodiArt'] = df_sql['KodiArt'].astype(str).str.strip()
        df_link['KODI'] = df_link['KODI'].astype(str).str.strip()
        
        # Merge 1: SQL + Sheet Produktet (per te marre KATEG.)
        df = pd.merge(df_sql, df_link[['KODI', 'KATEG.']], left_on='KodiArt', right_on='KODI', how='left')

        # Merge 2: Lidhja me emrat e kategorive (KATEG. -> KOD KAT)
        df_map['KOD KAT'] = df_map['KOD KAT'].astype(str).str.strip()
        df = pd.merge(df, df_map[['KOD KAT', 'EMER KAT', 'KG/SKU']], left_on='KATEG.', right_on='KOD KAT', how='left')

        # E. Kalkulimet Finale
        df['kg'] = df['Sasia'] * df['KG/SKU'].fillna(0)
        df['kat'] = df['EMER KAT'].fillna(df['KOD KAT']).fillna('ETJ')
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0)

        # Klasifikimi i grupeve
        def klasifiko_kategorine(k):
            val = str(k).upper()
            if "OLIM" in val or val == "V": 
                return "OLIM"
            elif "ETJ" in val: 
                return "ETJ"
            else: 
                return "DEKA"
        
        df['Grup_Filtri'] = df['kat'].apply(klasifiko_kategorine)

        return df

    except Exception as e:
        st.error(f"Gabim teknik: {e}")
        return None

# --- EKZEKUTIMI I DASHBOARD ---
if check_password():
    df_raw = load_all_data()

    if df_raw is not None:
        # Sidebar Navigimi
        st.sidebar.title("Menu")
        page = st.sidebar.selectbox("Zgjidh faqen", ["Dashboard Kryesor", "Analiza sipas Kategorive", "Planifikimi"])

        if page == "Dashboard Kryesor":
            st.title("📊 Pasqyra e Shitjeve")
            
            # Filtra baze
            selected_grup = st.sidebar.multiselect("Grup Filtri", options=df_raw['Grup_Filtri'].unique(), default=df_raw['Grup_Filtri'].unique())
            df_filtered = df_raw[df_raw['Grup_Filtri'].isin(selected_grup)]
            
            # Metrics
            total_kg = df_filtered['kg'].sum()
            total_vlera = df_filtered['Vlera_Historike'].sum()
            
            col1, col2 = st.columns(2)
            col1.metric("Total Shitje (KG)", f"{total_kg:,.0f}")
            col2.metric("Total Vlera (LEK)", f"{total_vlera:,.0f}")
            
            st.dataframe(df_filtered.head(100), use_container_width=True)

        elif page == "Planifikimi":
            st.title("📅 Planifikimi i Shitjeve")
            st.info("Kjo faqe eshte ne proces zhvillimi.")
    else:
        st.warning("Nuk u ngarkuan te dhenat. Kontrolloni skedarin 'prod.xlsx' dhe lidhjen me serverin.")
