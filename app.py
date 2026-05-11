import streamlit as st
import pandas as pd

st.set_page_config(page_title="Plani Shitjeve", layout="wide")

@st.cache_data(ttl=600)
def load_and_fix():
    file_name = 'SAD-DATAbase1.xlsb'
    # Lexojmë vetëm kolonat jetike
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'VleraRresht']
    
    try:
        # Leximi me engine pyxlsb
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip()
        
        # Konvertojmë datat menjëherë dhe optimizojmë tipet e të dhënave
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        
        # Llogarisim çmimin dhe fshijmë Vlerën për të kursyer RAM
        df['Cmimi'] = (df['VleraRresht'] / df['kg'].replace(0, 1)).round(2)
        df.drop(columns=['VleraRresht'], inplace=True)
        
        # Kthejmë kolonat e tekstit në string për të shmangur TypeError
        for col in ['ForcaShitese', 'Klienti', 'Artikulli', 'kat']:
            df[col] = df[col].astype(str).replace('nan', 'I papërcaktuar')
            
        return df
    except Exception as e:
        st.error(f"Serveri nuk mund ta hapë skedarin: {e}")
        return None

df = load_data_fixed = load_and_fix()

if df is not None:
    # 1. Gjejmë çmimin e fundit (përpara filtrimit të periudhës)
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi']]
    last_prices.rename(columns={'Cmimi': 'Cmimi_Fundit'}, inplace=True)

    # 2. Sidebar me dizajnin e ri
    st.sidebar.header("Parametrat")
    rritja = st.sidebar.number_input("Rritja (%)", value=10)
    
    # Filtri i Agjentit (i blinduar)
    agj_list = sorted(df['ForcaShitese'].unique().tolist())
    agj_sel = st.sidebar.selectbox("Agjenti:", ["Të gjithë"] + agj_list)
    
    # Filtri i Klientit
    k_list = df[df['ForcaShitese'] == agj_sel]['Klienti'].unique().tolist() if agj_sel != "Të gjithë" else df['Klienti'].unique().tolist()
    klientet = st.sidebar.multiselect("Klientët:", options=sorted([str(x) for x in k_list]))

    # 3. Llogaritjet
    # Marrim periudhën e fundit 3 mujore si default për të mos mbingarkuar llogaritjen
    dff = df.copy()
    if agj_sel != "Të gjithë":
        dff = dff[dff['ForcaShitese'] == agj_sel]
    if klientet:
        dff = dff[dff['Klienti'].isin(klientet)]

    # Grupimi
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({'kg': 'sum'}).reset_index()
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    
    # Supozojmë 12 muaj referencë nëse përdoruesi nuk zgjedh datë
    gp['Plani_KG'] = (gp['kg'] / 12 * (1 + rritja/100)).round(1)
    gp['Vlera'] = (gp['Plani_KG'] * gp['Cmimi_Fundit']).round(0)

    # 4. Shfaqja
    st.title("📊 Plani i Shitjeve")
    col1, col2 = st.columns(2)
    col1.metric("Total Plani KG", f"{gp['Plani_KG'].sum():,.0f}")
    col2.metric("Vlera Totale", f"{gp['Vlera'].sum():,.0f} L")

    st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Fundit', 'Plani_KG', 'Vlera']], use_container_width=True)