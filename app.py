import streamlit as st
import pandas as pd
from datetime import datetime
import base64

# 1. Konfigurimi i faqes
st.set_page_config(page_title="Sistemi i Planifikimit - DEKA SQL", layout="wide")

# Fjalori për Muajt Shqip
muajt_sq = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill", 5: "Maj", 6: "Qershor",
    7: "Korrik", 8: "Gusht", 9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor"
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
    if st.session_state["password"] == "admin123":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

if not check_password():
    st.stop()

# --- NAVIGIMI ---
st.sidebar.title("🧭 Menuja Kryesore")
page = st.sidebar.radio("Zgjidh Modulin:", ["Historiku", "Planifikimi", "Realizimi", "Mundësitë"])

# --- NGARKIMI I TE DHENAVE ---
@st.cache_data(ttl=3600)
def load_all_data():
    try:
        # A. Lidhja me SQL
        conn = st.connection("sql", type="sql")
        df_sql = conn.query("SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView")
        df_sql.columns = df_sql.columns.str.strip()
        df_sql['Data'] = pd.to_datetime(df_sql['Data'], errors='coerce')
        df_sql = df_sql.dropna(subset=['Data'])
        
        # B. Lidhja me Excel (Sheet: produktet, Kolona: KATEG.)
        df_map = pd.read_excel('produkte+.xlsx', sheet_name='produktet')
        df_map.columns = df_map.columns.str.strip()
        df_map = df_map[['KODI', 'KATEG.', 'KG/SKU']].copy()
        df_map['KODI'] = df_map['KODI'].astype(str).str.strip()
        
        # Merge
        df = pd.merge(df_sql, df_map, left_on='KodiArt', right_on='KODI', how='left')
        df['kg'] = df['Sasia'] * df['KG/SKU'].fillna(0)
        df.rename(columns={'KATEG.': 'kat'}, inplace=True)
        df['kat'] = df['kat'].fillna('ETJ')
        df['Vlera_Historike'] = pd.to_numeric(df['VleraRresht'], errors='coerce').fillna(0)
        
        # Klasifikimi i grupeve
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

df_raw = load_all_data()




# --- KETU FILLON PJESA QE DUHET TE FUSH ---

if df_raw is not None:
    # 1. Inicimi i Session State (Kjo mban mend zgjedhjet tua)
    if 'start_d' not in st.session_state:
        st.session_state['start_d'] = df_raw['Data'].min().date()
    if 'end_d' not in st.session_state:
        st.session_state['end_d'] = df_raw['Data'].max().date()
    if 'rritja_val' not in st.session_state:
        st.session_state['rritja_val'] = 10

    # 2. NDËRTIMI I SIDEBARIT (Menuja që do jetë kudo fiks si në foto)
    st.sidebar.header("⚙️ Kontrolli i Planit")
    
    date_range = st.sidebar.date_input(
        "Periudha referente:", 
        value=(st.session_state['start_d'], st.session_state['end_d'])
    )

    # Përditësojmë memorien nëse ndryshon data
    if isinstance(date_range, tuple) and len(date_range) == 2:
        st.session_state['start_d'], st.session_state['end_d'] = date_range

    rritja = st.sidebar.number_input("Rritja e planit (%)", value=st.session_state['rritja_val'])
    st.session_state['rritja_val'] = rritja

    grup_sel = st.sidebar.selectbox("Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"])
    
    agj_list = sorted([str(x) for x in df_raw['ForcaShitese'].unique() if x not in ['nan', 'None']])
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    k_list = df_raw[df_raw['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else df_raw['Klienti'].unique()
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin:", sorted(list(k_list)))

    # Shkurtesat për t'i përdorur më poshtë në kod
    start_date = st.session_state['start_d']
    end_date = st.session_state['end_d']

    # --- KETU FILLON LOGJIKA E FAQEVE ---

    #if page == "Planifikimi":
        #sot = datetime.now()
        #st.title(f"🎯 Plani: {muajt_sq.get(sot.month)} {sot.year}")
        # Vazhdo me pjesën tjetër të kodit të Planifikimit (gp, dff, etj.)
        # SHËNIM: Te Planifikimi, mos i kërko më filtrat nga sidebar sepse i llogaritëm sipër.

# ---------------------------------------------------------
# MODULI: PLANIFIKIMI
# ---------------------------------------------------------
if page == "Planifikimi" and df_raw is not None:
    sot = datetime.now()
    data_fundit_db = df_raw['Data'].max().strftime('%d/%m/%Y')

    # --- LOGJIKA E ÇMIMIT TË FUNDIT (Përjashton muajin korrent) ---
    # Marrim vetëm të dhënat që nuk i përkasin muajit dhe vitit aktual
    mask_past = (df_raw['Data'].dt.year < sot.year) | ((df_raw['Data'].dt.year == sot.year) & (df_raw['Data'].dt.month < sot.month))
    df_past = df_raw[mask_past].copy()
    df_past['Cmimi_Rresht'] = df_past['Vlera_Historike'] / df_past['kg'].replace(0, 1)
    last_prices = df_past.sort_values('Data').drop_duplicates('KodiArt', keep='last')[['KodiArt', 'Cmimi_Rresht']]
    last_prices.rename(columns={'Cmimi_Rresht': 'Cmimi_Fundit_Artikulli'}, inplace=True)

    # --- SIDEBAR ---
    #st.sidebar.header("⚙️ Kontrolli")
    #if st.sidebar.button("Log Out"):
        #st.session_state["password_correct"] = False
      #  st.rerun()

    #min_d, max_d = df_raw['Data'].min().date(), df_raw['Data'].max().date()
    #date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))
    #start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)
    
    #rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)
    #grup_sel = st.sidebar.selectbox("Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"])
    
    #agj_list = sorted([str(x) for x in df_raw['ForcaShitese'].unique() if x not in ['nan', 'None']])
    #agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)
    
    #k_list = df_raw[df_raw['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else #df_raw['Klienti'].unique()
    #klientet_selected = st.sidebar.multiselect("Zgjidh Klientin:", sorted(list(k_list)))

    # --- FILTRIMI ---
    mask = (df_raw['Data'].dt.date >= start_date) & (df_raw['Data'].dt.date <= end_date)
    dff = df_raw.loc[mask].copy()
    if grup_sel != "Të gjitha": dff = dff[dff['Grup_Filtri'] == grup_sel]
    if agj_sel != "Të gjithë": dff = dff[dff['ForcaShitese'] == agj_sel]
    if klientet_selected: dff = dff[dff['Klienti'].isin(klientet_selected)]

    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    # Ruajmë vlerat në session_state që t'i përdorim te Realizimi
    st.session_state['start_d_plani'] = start_date
    st.session_state['end_d_plani'] = end_date
    st.session_state['rritja_plani'] = rritja
    st.session_state['grup_plani'] = grup_sel

    # --- AGREGIMI ---
    gp = dff.groupby(['ForcaShitese', 'Klienti', 'kat', 'KodiArt', 'Artikulli']).agg({'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
    gp['Cmimi_Mes_Periudhes'] = (gp['Vlera_Historike'] / gp['kg'].replace(0, 1))
    gp = gp.merge(last_prices, on='KodiArt', how='left')
    gp['Plani_KG'] = (gp['kg'] / n_months) * (1 + rritja/100)
    gp['Vlera_Planifikuar'] = gp['Plani_KG'] * gp['Cmimi_Fundit_Artikulli'].fillna(gp['Cmimi_Mes_Periudhes'])

    # --- TITULLI DHE METRICS (Titulli tashmë është muaji korrent) ---
    st.title(f"🎯 Plani: {muajt_sq.get(sot.month)} {sot.year}")
    st.info(f"📅 Update i fundit: **{data_fundit_db}** | Grupi: **{grup_sel}**")

    t_kg_ref = gp['kg'].sum()
    t_v_ref = gp['Vlera_Historike'].sum()
    cm_mes_ref = t_v_ref / t_kg_ref if t_kg_ref > 0 else 0
    t_kg_plan = gp['Plani_KG'].sum()
    t_v_plan = gp['Vlera_Planifikuar'].sum()
    cm_mes_plan = t_v_plan / t_kg_plan if t_kg_plan > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Plani KG Totale", f"{t_kg_plan:,.0f}")
    c2.metric("Çmimi Mes. Periudhës", f"{cm_mes_ref:,.1f} L/kg")
    c3.metric("Çmimi Fundit Mes.", f"{cm_mes_plan:,.1f} L/kg", delta=f"{cm_mes_plan - cm_mes_ref:,.1f} L")
    c4.metric("Vlera Totale Plani", f"{t_v_plan:,.0f} L")

    config_kolonave = {
        "Cmimi_Mes_Periudhes": st.column_config.NumberColumn("Çmimi Mes. Periudhës", format="%.1f L"),
        "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn("Çmimi i Fundit", format="%.1f L"),
        "Cmimi_Mes_Grup": st.column_config.NumberColumn("Çmimi (Fundit) Mes.", format="%.1f L"),
        "Plani_KG": st.column_config.NumberColumn("Plani KG", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d")
    }

    st.divider()

    # --- TABET ---
    if klientet_selected:
        st.subheader("📍 Detajet Artikujve")
        st.dataframe(gp[['Klienti', 'kat', 'Artikulli', 'Cmimi_Mes_Periudhes', 'Cmimi_Fundit_Artikulli', 'Plani_KG', 'Vlera_Planifikuar']], 
                     width='stretch', hide_index=True, column_config=config_kolonave)
    else:
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        with t1:
            df_k = gp.groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_k['Cmimi_Mes_Periudhes'] = df_k['Vlera_Historike'] / df_k['kg'].replace(0, 1)
            df_k['Cmimi_Mes_Grup'] = df_k['Vlera_Planifikuar'] / df_k['Plani_KG'].replace(0, 1)
            st.dataframe(df_k[['kat', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         width='stretch', hide_index=True, column_config=config_kolonave)
        with t2:
            df_a = gp.groupby('ForcaShitese').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_a['Cmimi_Mes_Periudhes'] = df_a['Vlera_Historike'] / df_a['kg'].replace(0, 1)
            df_a['Cmimi_Mes_Grup'] = df_a['Vlera_Planifikuar'] / df_a['Plani_KG'].replace(0, 1)
            st.dataframe(df_a[['ForcaShitese', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         width='stretch', hide_index=True, column_config=config_kolonave)
        with t3:
            df_kl = gp.groupby(['Klienti', 'ForcaShitese']).agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum', 'kg': 'sum', 'Vlera_Historike': 'sum'}).reset_index()
            df_kl['Cmimi_Mes_Periudhes'] = df_kl['Vlera_Historike'] / df_kl['kg'].replace(0, 1)
            df_kl['Cmimi_Mes_Grup'] = df_kl['Vlera_Planifikuar'] / df_kl['Plani_KG'].replace(0, 1)
            st.dataframe(df_kl[['Klienti', 'ForcaShitese', 'Cmimi_Mes_Periudhes', 'Cmimi_Mes_Grup', 'Plani_KG', 'Vlera_Planifikuar']].sort_values('Plani_KG', ascending=False), 
                         width='stretch', hide_index=True, column_config=config_kolonave)

    # --- EKSPORTI ---
    def generate_html_report(dataframe):
        html = "<html><head><style>body{font-family:sans-serif;} table{width:100%; border-collapse:collapse;} th,td{border:1px solid #ddd; padding:8px; text-align:left;} th{background-color:#f2f2f2;} .num{text-align:right;}</style></head><body>"
        html += f"<h1>Raporti i Planit ({grup_sel})</h1>"
        for agjent in sorted(dataframe['ForcaShitese'].unique()):
            html += f"<h3>Agjenti: {agjent}</h3>"
            agj_df = dataframe[dataframe['ForcaShitese'] == agjent].groupby('kat').agg({'Plani_KG': 'sum', 'Vlera_Planifikuar': 'sum'}).reset_index()
            html += "<table><thead><tr><th>Kategoria</th><th class='num'>Plani (KG)</th><th class='num'>Vlera</th></tr></thead><tbody>"
            for _, row in agj_df.iterrows():
                html += f"<tr><td>{row['kat']}</td><td class='num'>{row['Plani_KG']:,.0f}</td><td class='num'>{row['Vlera_Planifikuar']:,.0f} L</td></tr>"
            html += "</tbody></table><br>"
        html += "</body></html>"
        return html

    if st.sidebar.button("Gjenero Raportin HTML"):
        b64 = base64.b64encode(generate_html_report(gp).encode()).decode()
        st.sidebar.markdown(f'<a href="data:text/html;base64,{b64}" download="Plani.html" style="padding:10px; background-color:#2e75b6; color:white; text-decoration:none; border-radius:5px;">Shkarko Raportin</a>', unsafe_allow_html=True)

# MODALET TJERA (Placeholder)
elif page == "Historiku": st.title("📚 Historiku i Shitjeve")

     
# ---------------------------------------------------------
# MODULI: REALIZIMI (Zëvendëso bllokun tënd me këtë)
# ---------------------------------------------------------
elif page == "Realizimi":
    sot = datetime.now()
    st.title(f"📈 Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")

    if df_raw is not None:
        # --- 1. LLOGARITJET (Target vs Real) ---
        mask_ref = (df_raw['Data'].dt.date >= start_date) & (df_raw['Data'].dt.date <= end_date)
        dff_ref = df_raw.loc[mask_ref].copy()
        
        if grup_sel != "Të gjitha": dff_ref = dff_ref[dff_ref['Grup_Filtri'] == grup_sel]
        if agj_sel != "Të gjithë": dff_ref = dff_ref[dff_ref['ForcaShitese'] == agj_sel]
        if klientet_selected: dff_ref = dff_ref[dff_ref['Klienti'].isin(klientet_selected)]

        n_months_ref = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))
        rritja_faktori = 1 + (rritja / 100)

        # Targeti
        gp_target = dff_ref.groupby(['kat']).agg({'kg': 'sum'}).reset_index()
        gp_target['KG_Target'] = (gp_target['kg'] / n_months_ref) * rritja_faktori

        # Realizimi Live
        mask_live = (df_raw['Data'].dt.year == sot.year) & (df_raw['Data'].dt.month == sot.month)
        df_live = df_raw[mask_live].copy()
        if grup_sel != "Të gjitha": df_live = df_live[df_live['Grup_Filtri'] == grup_sel]
        if agj_sel != "Të gjithë": df_live = df_live[df_live['ForcaShitese'] == agj_sel]
        if klientet_selected: df_live = df_live[df_live['Klienti'].isin(klientet_selected)]
        
        gp_live = df_live.groupby(['kat']).agg({'kg': 'sum'}).reset_index()
        gp_live.rename(columns={'kg': 'KG_Real'}, inplace=True)

        # Merge
        df_comp = pd.merge(gp_target[['kat', 'KG_Target']], gp_live, on='kat', how='left').fillna(0)
        
        # --- 2. METRIKAT KRYESORE ---
        t_target = df_comp['KG_Target'].sum()
        t_real = df_comp['KG_Real'].sum()
        perq_realizimit = (t_real / t_target * 100) if t_target > 0 else 0
        
        dita_sot = sot.day
        ditet_muajit = pd.Period(sot.strftime("%Y-%m")).days_in_month
        koha_perq = (dita_sot / ditet_muajit) * 100

        # Vizualizimi i Metrikave
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Target KG (Muaj)", f"{t_target:,.0f}")
        c2.metric("Realizuar KG", f"{t_real:,.0f}")
        
        # Ngjyra e realizimit: E kuqe nese jemi prapa kohes, e gjelber nese jemi para
        status_color = "normal" if perq_realizimit >= koha_perq else "inverse"
        c3.metric("Realizimi %", f"{perq_realizimit:.1f}%", 
                  delta=f"{perq_realizimit - koha_perq:.1f}% vs Koha", delta_color=status_color)
        
        c4.metric("Koha e kaluar", f"{koha_perq:.1f}%", f"{dita_sot}/{ditet_muajit} Ditë")

        st.divider()

        # --- 3. TABET ---
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])

        with t1:
            df_comp['Progresi'] = (df_comp['KG_Real'] / df_comp['KG_Target'] * 100).clip(upper=100)
            st.dataframe(
                df_comp.sort_values('KG_Target', ascending=False),
                column_config={
                    "kat": "Kategoria",
                    "KG_Target": st.column_config.NumberColumn("Target (KG)", format="%d"),
                    "KG_Real": st.column_config.NumberColumn("Realizuar (KG)", format="%d"),
                    "Progresi": st.column_config.ProgressColumn("Ecuria %", min_value=0, max_value=100, format="%.1f%%")
                },
                hide_index=True, use_container_width=True
            )

        with t2:
            # Agregimi për Agjentët
            gp_agj_t = dff_ref.groupby('ForcaShitese').agg({'kg': 'sum'}).reset_index()
            gp_agj_t['Target'] = (gp_agj_t['kg'] / n_months_ref) * rritja_faktori
            gp_agj_l = df_live.groupby('ForcaShitese').agg({'kg': 'sum'}).reset_index()
            gp_agj_l.rename(columns={'kg': 'Real'}, inplace=True)
            df_agj = pd.merge(gp_agj_t[['ForcaShitese', 'Target']], gp_agj_l, on='ForcaShitese', how='left').fillna(0)
            df_agj['%'] = (df_agj['Real'] / df_agj['Target'] * 100).clip(upper=100)
            st.dataframe(df_agj.sort_values('%', ascending=False), hide_index=True, use_container_width=True)

        with t3:
            # Agregimi për Klientët
            gp_kl_t = dff_ref.groupby(['Klienti', 'ForcaShitese']).agg({'kg': 'sum'}).reset_index()
            gp_kl_t['Target'] = (gp_kl_t['kg'] / n_months_ref) * rritja_faktori
            gp_kl_l = df_live.groupby('Klienti').agg({'kg': 'sum'}).reset_index()
            gp_kl_l.rename(columns={'kg': 'Real'}, inplace=True)
            df_kl = pd.merge(gp_kl_t[['Klienti', 'ForcaShitese', 'Target']], gp_kl_l, on='Klienti', how='left').fillna(0)
            df_kl['%'] = (df_kl['Real'] / df_kl['Target'] * 100).clip(upper=100)
            st.dataframe(df_kl[df_kl['Target'] > 0].sort_values('%', ascending=False), hide_index=True, use_container_width=True)

# Mesazh paralajmërues nëse jemi prapa
            t_real_tot = df_comp['KG_Real'].sum()
            t_target_tot = df_comp['KG_Target'].sum()
            total_perc = (t_real_tot / t_target_tot * 100) if t_target_tot > 0 else 0
            
            if total_perc < koha_perq:
                st.error(f"🔴 Jeni prapa! Realizimi: {total_perc:.1f}% | Koha e kaluar: {koha_perq:.1f}%")
            else:
                st.success(f"🟢 Shumë mirë! Realizimi: {total_perc:.1f}% | Koha e kaluar: {koha_perq:.1f}%")

elif page == "Mundësitë": st.title("🔍 Mundësitë & Risk Profile")