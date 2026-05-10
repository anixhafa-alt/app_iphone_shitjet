import streamlit as st
import pandas as pd

# 1. Konfigurimi i faqes (Mobile Friendly)
st.set_page_config(
    page_title="Planifikimi Shitjeve",
    page_icon="📊",
    layout="wide"
)

# 2. Funksioni i optimizuar për leximin e të dhënave
@st.cache_data
def load_data():
    # Emri i skedarit fiks siç është në GitHub
    file_name = 'SAD-DATAbase1.xlsb'
    
    # Lexojmë vetëm kolonat që na duhen për të kursyer RAM-in e serverit
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat']
    
    try:
        # Leximi i skedarit XLSB
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        
        # Pastrimi i emrave të kolonave nga hapësirat ose thonjëzat
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # Konvertimi i datës nga formati Excel (numër) në formatin Data
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        return df
    except Exception as e:
        st.error(f"Gabim gjatë leximit: {e}")
        return None

# Ngarkojmë të dhënat në memorje
df = load_data()

if df is not None:
    # --- FILTRAT (Sidebar) ---
    st.sidebar.header("🔍 Filtrat")

    # Filtri i Agjentit - I blinduar kundër TypeError
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjentet = st.sidebar.multiselect("Zgjidh Forcën Shitëse:", options=agj_list)
    
    # Kërkimi i Klientit
    search_klient = st.sidebar.text_input("Kërko Klientin:")
    
    # Filtri i Kategorisë - I blinduar kundër TypeError
    kat_list = sorted([str(x) for x in df['kat'].unique() if pd.notna(x)])
    kategorite = st.sidebar.multiselect("Filtro sipas Kategorisë:", options=kat_list)

    # --- LOGJIKA E FILTRIMIT ---
    filtered_df = df.copy()
    
    if agjentet:
        filtered_df = filtered_df[filtered_df['ForcaShitese'].astype(str).isin(agjentet)]
    
    if search_klient:
        filtered_df = filtered_df[filtered_df['Klienti'].str.contains(search_klient, case=False, na=False)]
        
    if kategorite:
        filtered_df = filtered_df[filtered_df['kat'].astype(str).isin(kategorite)]

    # --- KALKULIMET ---
    # Gjejmë numrin e muajve unikë për të llogaritur objektivin
    unique_months = df['Data'].dt.to_period('M').nunique()
    if unique_months == 0: unique_months = 1
    
    # Agregimi: Mbledhim KG për çdo kombinim
    summary = filtered_df.groupby(['ForcaShitese', 'Klienti', 'Artikulli', 'kat'])['kg'].sum().reset_index()
    
    # Llogaritja e Objektivit Mujor (Mesatarja e kg për muaj)
    summary['Objektivi_Mujor'] = (summary['kg'] / unique_months).round(1)
    
    # Renditja sipas shitjeve më të larta
    summary = summary.sort_values(by='kg', ascending=False)

    # --- SHFAQJA NË EKRAN ---
    st.title("📊 Sistemi i Planifikimit")
    st.info(f"Kalkulimi bazohet në {unique_months} muaj të dhëna.")

    # Tabela kryesore e detajuar
    st.subheader("📋 Detajet e Planit")
    st.dataframe(
        summary[['ForcaShitese', 'Klienti', 'Artikulli', 'Objektivi_Mujor', 'kg']],
        use_container_width=True,
        hide_index=True
    )

    # Butoni për shkarkim (nëse të duhet në Excel/CSV përsëri)
    csv = summary.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Shkarko Raportin",
        data=csv,
        file_name="plani_shitjeve.csv",
        mime="text/csv",
    )
else:
    st.warning("Skedari nuk u gjet. Sigurohu që 'SAD-DATAbase1.xlsb' është në GitHub.")