import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import base64

# 1. Konfigurimi i faqes
st.set_page_config(page_title="Sistemi i Planifikimit - DEKA SQL", layout="wide")

# --- SISTEMI I SIGURISE ---
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
    if st.session_state["password"] == "admin123":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()

# --- NGARKIMI I TE DHENAVE (SQL + EXCEL MAPPING) ---
@st.cache_data(ttl=3600)
def load_data_combined():
    try:
        conn = st.connection("sql", type="sql")
        sql_query = "SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView"
        df_sql = conn.query(sql_query)
        
        if df_sql is None or df_sql.empty:
            st.error("SQL nuk ktheu të dhëna!")
            return None

        df_sql.columns = df_sql.columns.str.strip()
        df_sql['KodiArt'] = df_sql['KodiArt'].astype(str).str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data'])

        # Leximi i Sheet: produktet
        df_mapping = pd.read_excel('produkte+.xlsx', sheet_name='produktet')
        df_mapping.columns = df_mapping.columns.str.strip()
        df_mapping = df_mapping[['KODI', 'KATEG.', 'KG/SKU']].copy()
        df_mapping['KODI'] = df_mapping['KODI'].astype(str).str.strip()
        df_mapping['KG/SKU'] = pd.to_numeric(df_mapping['KG/SKU'], errors='coerce').fillna(0)

        # Merge dhe Llogaritja e KG
        df = pd.merge(df_sql, df_mapping, left_on='KodiArt', right_on='KODI', how='left')
        df['kg'] = df['Sasia'] * df['KG/SKU']
        df.rename(columns={'KATEG.': 'kat'}, inplace=True)
        df['kat'] = df['kat'].fillna('ETJ')
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0).astype('float32')

        def klasifiko_kategorine(k):
            val = str(k).upper()
            if val == "V" or "OLIM" in val: return "OLIM"
            elif val == "ETJ": return "ETJ"
            else: return "DEKA"
        
        df['Grup_Filtri'] = df['kat'].apply(klasifiko_kategorine)
        return df
    except Exception as e:
        st.error(f"Gabim teknik: {e}")
        return None

df = load_data_combined()

if df is not None and not df.empty:
    # Cmimi i fundit historik
    df['Cmimi_Rresht'] = (df['Vlera_Historike'] / df['kg'].replace(0, 1))
    last_prices = df.sort_values('Data').drop_duplicates('KodiArt', keep='last')[['KodiArt', 'Cmimi_Rresht']]
    last_prices.rename(columns={'Cmimi_Rresht': 'Cmimi_Fundit_Artikulli'}, inplace=True)

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Kontrolli")
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()

    min_d, max_d = df['Data'].min().date(), df['Data'].max().date()
    date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
    start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
    
    rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)
    grupet_list = ["Të gjitha", "OLIM", "ETJ", "DEKA"]
    grup_sel = st.sidebar.selectbox("Filtro Grupin:", grupet_list)
    
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x not in ['nan', 'None']])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)

    # --- FILTRIMI DHE LLOGARITJET ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()
    if grup_sel != "Të gjitha": dff = dff[dff['Grup_Filtri'] == grup_sel]
    if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]

    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'KodiArt', 'Artikulli']).agg({'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
    gp['Cmimi_Mes_Periudhes'] = (gp['Vlera_Historike'] / gp['kg'].replace(0, 1))
    gp = gp.merge(last_prices, on='KodiArt', how='left')
    gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
    gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli']

    # --- TITULLI DHE INFO ---
    st.title("🎯 Sistemi i Planifikimit Real-Time")
    max_dt = df['Data'].max().strftime('%d/%m/%Y') if pd.notnull(df['Data'].max()) else "N/A"
    st.info(f"📅 Burimi: **SQL Server** | Update i fundit: **{max_dt}** | Periudha: **{n_months} muaj**")

    # --- METRICS ---
    t_kg = gp['Plani_KG'].sum()
    t_vl = gp['Vlera_Planifikuar'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Totali KG Plan", f"{t_kg:,.0f} kg")
    c2.metric("Totali Vlerë Plan", f"{t_vl:,.0f} L")
    c3.metric("Rritja e Aplikuar", f"{rritja}%")

    st.divider()

    # --- VISUALIZIMI ---
    col_left, col_right = st.columns([1, 1])
    with col_left:
        fig_kat = px.pie(gp, values='Plani_KG', names='kat', hole=0.4, title="Shpërndarja sipas Kategorive (KG)")
        st.plotly_chart(fig_kat, use_container_width=True)
    with col_right:
        df_agj_chart = gp.groupby('ForcaShitese')['Plani_KG'].sum().reset_index()
        fig_agj = px.pie(df_agj_chart, values='Plani_KG', names='ForcaShitese', hole=0.4, title="Shpërndarja sipas Agjentëve (KG)")
        st.plotly_chart(fig_agj, use_container_width=True)

    # --- TABET ME DETAJE ---
    t1, t2, t3, t4 = st.tabs(["📊 Sipas Kategorive", "👤 Sipas Agjentëve", "🏪 Sipas Klientëve", "📦 Detajet e Artikujve"])
    
    config_std = {
        "Plani_KG": st.column_config.NumberColumn("KG Plan", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Plan", format="%d L"),
        "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn("Çmimi Fundit", format="%.1f L")
    }

    with t1:
        st.dataframe(gp.groupby('kat').agg({'Plani_KG':'sum', 'Vlera_Planifikuar':'sum'}).reset_index().sort_values('Plani_KG', ascending=False), hide_index=True, use_container_width=True, column_config=config_std)
    with t2:
        st.dataframe(gp.groupby('ForcaShitese').agg({'Plani_KG':'sum', 'Vlera_Planifikuar':'sum'}).reset_index().sort_values('Plani_KG', ascending=False), hide_index=True, use_container_width=True, column_config=config_std)
    with t3:
        st.dataframe(gp.groupby(['Klienti', 'ForcaShitese']).agg({'Plani_KG':'sum', 'Vlera_Planifikuar':'sum'}).reset_index().sort_values('Plani_KG', ascending=False), hide_index=True, use_container_width=True, column_config=config_std)
    with t4:
        st.dataframe(gp[['Artikulli', 'kat', 'Plani_KG', 'Cmimi_Fundit_Artikulli', 'Vlera_Planifikuar']], hide_index=True, use_container_width=True, column_config=config_std)

    # --- EKSPORTI HTML ---
    def generate_html_report(dataframe):
        html = f"<html><head><style>body{{font-family:sans-serif;}} table{{width:100%; border-collapse:collapse; margin-bottom:30px;}} th,td{{border:1px solid #ddd; padding:8px; text-align:left;}} th{{background-color:#f2f2f2;}} .num{{text-align:right;}} .total-row{{font-weight:bold; background-color:#eef2f7;}}</style></head><body>"
        html += f"<h1>Raporti i Planit - Grupi {grup_sel}</h1>"
        for agjent in sorted(dataframe['ForcaShitese'].unique()):
            html += f"<h2>Agjenti: {agjent}</h2>"
            agj_df = dataframe[dataframe['ForcaShitese'] == agjent]
            kat_df = agj_df.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            html += "<table><thead><tr><th>Kategoria</th><th class='num'>Plani (KG)</th><th class='num'>Vlera e Planit</th></tr></thead><tbody>"
            for _, row in kat_df.iterrows():
                html += f"<tr><td>{row['kat']}</td><td class='num'>{row['Plani_KG']:,.0f}</td><td class='num'>{row['Vlera_Planifikuar']:,.0f} L</td></tr>"
            html += f"<tr class='total-row'><td>TOTAL {agjent}</td><td class='num'>{kat_df['Plani_KG'].sum():,.0f}</td><td class='num'>{kat_df['Vlera_Planifikuar'].sum():,.0f} L</td></tr>"
            html += "</tbody></table>"
        html += "</body></html>"
        return html

    if st.sidebar.button("Gjenero Raportin HTML"):
        report_content = generate_html_report(gp)
        b64 = base64.b64encode(report_content.encode()).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="Plani_Deka_SQL.html" style="padding:10px; background-color:#2e75b6; color:white; text-decoration:none; border-radius:5px;">Shkarko Raportin</a>'
        st.sidebar.markdown(href, unsafe_allow_html=True)