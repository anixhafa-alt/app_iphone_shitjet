import streamlit as st
import pandas as pd
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
    # NDRYSHO "admin123" me fjalëkalimin që dëshiron
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
        # A. Lidhja me SQL duke perdorur Sekretet (pymssql)
        conn = st.connection("sql", type="sql")
        sql_query = "SELECT Data, ForcaShitese, Klienti, Artikulli, kg, VleraRresht FROM dbo.GetRaportiMadhView"
        df_sql = conn.query(sql_query)
        
        if df_sql is None or df_sql.empty:
            st.error("SQL nuk ktheu asnjë të dhënë!")
            return None

        # B. Pastrimi i te dhenave SQL
        df_sql.columns = df_sql.columns.str.strip()
        df_sql['Artikulli'] = df_sql['Artikulli'].astype(str).str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data']) # Heqim rreshtat pa date te vlefshme

        # C. Merr kategoritë nga Excel-i 'produkte+.xlsx'
        # Artikulli = EMERTIMI dhe kat = KATEG
        df_mapping = pd.read_excel('produkte+.xlsx')
        df_mapping = df_mapping[['EMERTIMI', 'KATEG']].copy()
        df_mapping['EMERTIMI'] = df_mapping['EMERTIMI'].astype(str).str.strip()
        df_mapping['KATEG'] = df_mapping['KATEG'].astype(str).str.strip()

        # D. Bashkimi (Merge)
        df = pd.merge(df_sql, df_mapping, left_on='Artikulli', right_on='EMERTIMI', how='left')
        
        # Rregullojmë emrin e kolonës së kategorisë
        df.rename(columns={'KATEG': 'kat'}, inplace=True)
        df['kat'] = df['kat'].fillna('ETJ')

        # Formatime numerike
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0).astype('float32')

        # Logjika e grupimit të kërkuar
        def klasifiko_kategorine(k):
            val = str(k).upper()
            if val == "V" or "OLIM" in val:
                return "OLIM"
            elif val == "ETJ":
                return "ETJ"
            else:
                return "DEKA"
        
        df['Grup_Filtri'] = df['kat'].apply(klasifiko_kategorine)
        return df

    except Exception as e:
        st.error(f"Gabim gjatë lidhjes: {e}")
        return None

df = load_data_combined()

if df is not None and not df.empty:
    # Llogaritja e çmimit të fundit
    df['Cmimi_Rresht'] = (df['Vlera_Historike'] / df['kg'].replace(0, 1))
    last_prices = df.sort_values('Data').drop_duplicates('Artikulli', keep='last')[['Artikulli', 'Cmimi_Rresht']]
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
    grup_sel = st.sidebar.selectbox("Filtro Grupin (OLIM/ETJ/DEKA):", grupet_list)
    
    agj_list = sorted([str(x) for x in df['ForcaShitese'].unique() if x not in ['nan', 'None']])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)

    # --- FILTRIMI ---
    mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
    dff = df.loc[mask].copy()
    if grup_sel != "Të gjitha": dff = dff[dff['Grup_Filtri'] == grup_sel]
    if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]

    # Llogaritja e muajve
    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    # --- AGREGIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'Artikulli']).agg({'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
    gp['Cmimi_Mes_Periudhes'] = (gp['Vlera_Historike'] / gp['kg'].replace(0, 1))
    gp = gp.merge(last_prices, on='Artikulli', how='left')
    gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
    gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli']

    # --- TITULLI DHE INFO ---
    st.title("🚀 Plani Real-Time (SQL Server)")
    max_date = df['Data'].max()
    last_update_str = max_date.strftime('%d/%m/%Y') if pd.notnull(max_date) else "Pa datë"
    st.info(f"📅 Update i fundit nga SQL: **{last_update_str}** | Grupi: **{grup_sel}**")

    # --- METRICS ---
    t_kg_plan = gp['Plani_KG'].sum()
    t_v_plan = gp['Vlera_Planifikuar'].sum()
    cm_mes_plan = t_v_plan / t_kg_plan if t_kg_plan > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Plani KG Totale", f"{t_kg_plan:,.0f}")
    c2.metric("Çmimi Fundit (Ponderuar)", f"{cm_mes_plan:,.1f} L/kg")
    c3.metric("Vlera Totale Plani", f"{t_v_plan:,.0f} L")

    st.divider()

    # --- TABET ---
    t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
    config_kol = {
        "Cmimi_Mes_Periudhes": st.column_config.NumberColumn("Çmimi Mes. Hist", format="%.1f L"),
        "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn("Çmimi i Fundit", format="%.1f L"),
        "Plani_KG": st.column_config.NumberColumn("KG Plan", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d")
    }

    with t1:
        df_k = gp.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
        st.dataframe(df_k.sort_values('Plani_KG', ascending=False), width='stretch', hide_index=True, column_config=config_kol)
    with t2:
        df_a = gp.groupby('ForcaShitese').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
        st.dataframe(df_a.sort_values('Plani_KG', ascending=False), width='stretch', hide_index=True, column_config=config_kol)
    with t3:
        df_kl = gp.groupby(['Klienti', 'ForcaShitese']).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
        st.dataframe(df_kl.sort_values('Plani_KG', ascending=False), width='stretch', hide_index=True, column_config=config_kol)

    # --- EKSPORTI ---
    def generate_html_report(dataframe):
        html = f"<html><head><style>body{{font-family:sans-serif;}} table{{width:100%; border-collapse:collapse; margin-bottom:30px;}} th,td{{border:1px solid #ddd; padding:8px; text-align:left;}} th{{background-color:#f2f2f2;}} .num{{text-align:right;}} .total-row{{font-weight:bold; background-color:#eef2f7;}}</style></head><body>"
        html += f"<h1>Raporti i Planit ({grup_sel})</h1>"
        for agjent in sorted(dataframe['ForcaShitese'].unique()):
            html += f"<h2>Agjenti: {agjent}</h2>"
            agj_df = dataframe[dataframe['ForcaShitese'] == agjent]
            kat_df = agj_df.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            kat_df['Cmimi'] = kat_df['Vlera_Planifikuar'] / kat_df['Plani_KG'].replace(0, 1)
            
            html += "<table><thead><tr><th>Kategoria</th><th class='num'>Çmimi Fundit</th><th class='num'>Plani (KG)</th></tr></thead><tbody>"
            for _, row in kat_df.iterrows():
                html += f"<tr><td>{row['kat']}</td><td class='num'>{row['Cmimi']:,.1f} L</td><td class='num'>{row['Plani_KG']:,.0f}</td></tr>"
            
            t_kg_a = kat_df['Plani_KG'].sum()
            t_vl_a = kat_df['Vlera_Planifikuar'].sum()
            t_cm_a = t_vl_a / t_kg_a if t_kg_a > 0 else 0
            html += f"<tr class='total-row'><td>TOTALI {agjent}</td><td class='num'>{t_cm_a:,.1f} L</td><td class='num'>{t_kg_a:,.0f}</td></tr>"
            html += "</tbody></table>"
        html += "</body></html>"
        return html

    if st.sidebar.button("Gjenero Raportin HTML"):
        report_content = generate_html_report(gp)
        b64 = base64.b64encode(report_content.encode()).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="Plani_{grup_sel}.html" style="padding:10px; background-color:#2e75b6; color:white; text-decoration:none; border-radius:5px;">Shkarko Raportin</a>'
        st.sidebar.markdown(href, unsafe_allow_html=True)