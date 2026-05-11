import streamlit as st
import pandas as pd

# 1. Konfigurimi
st.set_page_config(page_title="Planifikimi Profesional", layout="wide")

@st.cache_data
def load_data():
    file_name = 'SAD-DATAbase1.xlsb'
    # Shtohen kolonat 'Vlera' (ose siç e ke në Excel) për pikën 7
    cols = ['Data', 'ForcaShitese', 'Klienti', 'Artikulli', 'kg', 'kat', 'Vlera']
    
    try:
        df = pd.read_excel(file_name, engine='pyxlsb', usecols=cols)
        df.columns = df.columns.str.strip().str.replace('"', '')
        df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30')
        return df
    except Exception as e:
        st.error(f"Gabim në lexim: Sigurohu që kolona 'Vlera' ekziston në Excel. Error: {e}")
        return None

df = load_data()

if df is not None:
    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Parametrat")
    
    date_range = st.sidebar.date_input(
        "Periudha referente:",
        value=(df['Data'].min().date(), df['Data'].max().date())
    )
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = df['Data'].min().date(), df['Data'].max().date()

    rritja_perqindje = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # Filtrat
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if pd.notna(x)])
    agjenti_select = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    search_klient = st.sidebar.text_input("Kërko Klientin:")

    # --- FILTRIMI ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()

    if agjenti_select != "Të gjithë":
        dff = dff[dff['ForcaShitese'].astype(str) == agjenti_select]
    if search_klient:
        dff = dff[dff['Klienti'].str.contains(search_klient, case=False, na=False)]

    delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    n_months = max(1, delta)

    # --- LLOGARITJET (Pika 7: Cmimi Mesatar) ---
    # Grupojmë për të marrë totalet për artikull
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({
        'kg': 'sum',
        'Vlera': 'sum'
    }).reset_index()
    
    # Cmimi Mesatar = Vlera Totale / KG Totale
    gp['Cmimi_Mesatar'] = (gp['Vlera'] / gp['kg']).round(2)
    gp['Plani_KG'] = ((gp['kg'] / n_months) * (1 + rritja_perqindje/100)).round(1)
    gp['Vlera_Planifikuar'] = (gp['Plani_KG'] * gp['Cmimi_Mesatar']).round(2)

    # --- DISPLAY ---
    next_month = (pd.to_datetime(end_date) + pd.DateOffset(months=1))
    st.title(f"🎯 Plani: {next_month.strftime('%B %Y')}")

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Total KG Referenca", f"{gp['kg'].sum():,.0f}")
    c2.metric(f"Plani KG (+{rritja_perqindje}%)", f"{gp['Plani_KG'].sum():,.0f}")
    c3.metric("Vlera e Parashikuar", f"{gp['Vlera_Planifikuar'].sum():,.0f} Lekë")

    st.divider()

    if search_klient:
        st.subheader(f"📍 Plani i detajuar: {search_klient}")
        # Shfaqim Kategorinë, Artikullin, Cmimin dhe Planin
        klient_df = gp.groupby(['kat', 'Artikulli', 'Cmimi_Mesatar'])['Plani_KG'].sum().reset_index()
        st.dataframe(klient_df, use_container_width=True, hide_index=True)
    else:
        # TABS (Shtuar Tab i Klientëve)
        t1, t2, t3 = st.tabs(["Sipas Kategorive", "Sipas Agjentëve", "Sipas Klientëve"])
        
        with t1:
            kat_view = gp.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            st.dataframe(kat_view.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)
            
        with t2:
            agj_view = gp.groupby('ForcaShitese').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            st.dataframe(agj_view.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)

        with t3:
            # Lista e plotë e Klientëve me totalet e tyre
            klient_list = gp.groupby(['Klienti', 'ForcaShitese']).agg({
                'Plani_KG': 'sum',
                'Vlera_Planifikuar': 'sum'
            }).reset_index()
            st.dataframe(klient_list.sort_values('Plani_KG', ascending=False), use_container_width=True, hide_index=True)