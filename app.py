import streamlit as st
import pandas as pd

# 1. Konfigurimi i faqes për iPhone (Mobile Friendly)
st.set_page_config(
    page_title="Planifikimi Shitjeve",
    page_icon="📊",
    layout="wide"
)

# 2. Funksioni për leximin e të dhënave (Me Cache që të mos rëndojë serverin)
@st.cache_data
def load_data():
    # KUJDES: Emri i skedarit duhet të jetë fiks si në GitHub
    file_name = 'SAD-DATAbase1.xlsb'
    
    # Lexojmë vetëm kolonat që na duhen për Dashboard
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat']
    
    try:
        # Leximi i optimizuar
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        
        # Pastrimi i emrave të kolonave
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # Konvertimi i dates
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        return df
    except Exception as e:
        st.error(f"Gabim gjatë leximit të skedarit: {e}")
        return None

# Ngarkojmë të dhënat
df = load_data()

if df is not None:
    # --- INTERFAQA (Dizajni) ---
    st.title("📊 Sistemi i Planifikimit")
    
    # Sidebar për filtrat
    st.sidebar.header("Filtrat e Kërkimit")
    
    # 1. Filtri i Agjentit (I rregulluar)
    # Kthejmë çdo gjë në tekst dhe heqim vlerat bosh që të mos japë error sorted()
    lista_agjenteve = df['ForcaShitese'].astype(str).unique().tolist()
    agjentet = st.sidebar.multiselect(
        "Zgjidh Forcën Shitëse:",
        options=sorted([x for x in lista_agjenteve if x != 'nan'])
    )
    
    # 2. Kërkimi i Klientit
    search_klient = st.sidebar.text_input("Kërko Klientin (Shkruaj emrin):")
    
    # 3. Filtri i Kategorisë (I rregulluar)
    lista_kat = df['kat'].astype(str).unique().tolist()
    kategorite = st.sidebar.multiselect(
        "Filtro sipas Kategorisë:",
        options=sorted([x for x in lista_kat if x != 'nan'])
    )
    
    # --- APLIKIMI I FILTRAVE ---
    filtered_df = df.copy()
    
    if agjentet:
        filtered_df = filtered_df[filtered_df['ForcaShitese'].isin(agjentet)]
    
    if search_klient:
        filtered_df = filtered_df[filtered_df['Klienti'].str.contains(search_klient, case=False, na=False)]
        
    if kategorite:
        filtered_df = filtered_df[filtered_df['kat'].isin(kategorite)]

    # --- SHPALLJA E REZULTATEVE ---
    
    # Llogarisim muajt unikë për planin
    unique_months = df['Data'].dt.to_period('M').nunique()
    if unique_months == 0: unique_months = 1
    
    st.info(f"📅 Të dhënat bazohen në {unique_months} muaj shitje.")

    # Agregimi i të dhënave (Përmbledhje)
    summary = filtered_df.groupby(['ForcaShitese', 'Klienti', 'Artikulli', 'kat'])['kg'].sum().reset_index()
    
    # Llogarisim Objektivin Mesatar (kg / muaj)
    summary['Objektivi_Mujor'] = (summary['kg'] / unique_months).round(1)
    
    # Renditja
    summary = summary.sort_values(by='kg', ascending=False)

    # Shfaqja e tabelës kryesore
    st.subheader("📋 Detajet e Planifikimit")
    st.dataframe(
        summary[['ForcaShitese', 'Klienti', 'Artikulli', 'Objektivi_Mujor', 'kg']],
        use_container_width=True,
        hide_index=True
    )

    # Opsion për shkarkim (Nëse të duhet në iPhone)
    csv = summary.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Shkarko këtë raport (CSV)",
        csv,
        "plani_export.csv",
        "text/csv",
        key='download-csv'
    )