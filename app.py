import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image
import os
import base64
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# =========================================================
# 1. KONFIGURIMI I FAQES
# =========================================================
st.set_page_config(
    page_title="Sistemi i Planifikimit - DEKA SQL",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Global - Design i përmirësuar
st.markdown("""
<style>
/* Font dhe bazë */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Fshij ngjyrën e bardhë të sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #cbd5e1 !important;
    font-size: 0.9rem;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #94a3b8 !important;
    font-size: 0.8rem;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    color: #64748b !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600 !important;
}

/* Tituj faqesh */
h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    letter-spacing: -0.02em;
    border-bottom: 3px solid #3b82f6;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem !important;
}
h2, h3 {
    color: #1e293b !important;
    font-weight: 600 !important;
}

/* Buton kryesor */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.875rem;
    padding: 0.5rem 1.25rem;
    transition: all 0.2s;
    box-shadow: 0 2px 4px rgba(37,99,235,0.3);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.4);
}

/* Tab stil */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f1f5f9;
    padding: 4px;
    border-radius: 10px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    font-weight: 500;
    color: #64748b;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #1e293b !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}

/* Sidebar version badge */
.version-badge {
    display: inline-block;
    background: rgba(59,130,246,0.2);
    color: #93c5fd !important;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 20px;
    letter-spacing: 0.05em;
    text-align: center;
    width: 100%;
    margin-bottom: 16px;
}

/* KPI Card custom */
.kpi-card {
    background: linear-gradient(135deg, #1e40af, #3b82f6);
    border-radius: 14px;
    padding: 20px 24px;
    color: white;
    margin-bottom: 12px;
}
.kpi-label { font-size: 0.75rem; opacity: 0.8; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-value { font-size: 2rem; font-weight: 700; margin: 4px 0; }
.kpi-delta { font-size: 0.8rem; opacity: 0.9; }

/* Alert/info box */
.info-banner {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0 16px 0;
    font-size: 0.875rem;
    color: #1e40af;
}

/* Leaderboard */
.rank-1 { background: linear-gradient(135deg, #fef3c7, #fde68a); border-radius: 10px; padding: 12px; }
.rank-2 { background: linear-gradient(135deg, #f1f5f9, #e2e8f0); border-radius: 10px; padding: 12px; }
.rank-3 { background: linear-gradient(135deg, #fef3c7, #fed7aa); border-radius: 10px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# Fjalori për Muajt Shqip
muajt_sq = {
    1: "Janar", 2: "Shkurt", 3: "Mars", 4: "Prill",
    5: "Maj", 6: "Qershor", 7: "Korrik", 8: "Gusht",
    9: "Shtator", 10: "Tetor", 11: "Nëntor", 12: "Dhjetor",
}

# =========================================================
# 2. SISTEMI I SIGURISE (LOGIN) - I PËRMIRËSUAR
# =========================================================
# SHËNIM: Fjalëkalimi duhet të vendoset te st.secrets["app_password"]
# Fallback te "deka2024" nëse nuk ka secrets (vetëm për dev)
def merr_fjalekalimin():
    try:
        return st.secrets["app_password"]
    except Exception:
        return "deka2024"

def password_entered():
    if st.session_state["password"] == merr_fjalekalimin():
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("""
        <div style='max-width:380px; margin:80px auto; text-align:center;'>
            <div style='font-size:3rem; margin-bottom:8px;'>🔐</div>
            <h2 style='color:#0f172a; font-size:1.5rem; border:none; margin-bottom:4px;'>Hyrja në Sistem</h2>
            <p style='color:#64748b; font-size:0.9rem;'>DEKA SQL · Sistemi i Planifikimit</p>
        </div>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Fjalëkalimi:", type="password",
                          on_change=password_entered, key="password",
                          placeholder="Shkruaj fjalëkalimin...")
        return False
    elif not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("❌ Fjalëkalim i gabuar! Provo sërish:",
                          type="password", on_change=password_entered,
                          key="password")
        return False
    return True

if not check_password():
    st.stop()

# =========================================================
# 3. LOGO DHE SIDEBAR
# =========================================================
EMRI_FOTOS = "logo.png"
if os.path.exists(EMRI_FOTOS):
    try:
        logo_axion = Image.open(EMRI_FOTOS)
        st.sidebar.image(logo_axion, use_container_width=True)
    except Exception as e:
        st.sidebar.title("DEKA SQL")
else:
    st.sidebar.markdown("""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <span style='font-size:1.4rem; font-weight:700; color:#e2e8f0; letter-spacing:2px;'>DEKA SQL</span>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown('<div class="version-badge">v4.0.0</div>', unsafe_allow_html=True)

# =========================================================
# 4. NAVIGIMI
# =========================================================
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.1);">
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none"
         stroke="#60a5fa" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1.5"></rect>
        <rect x="14" y="3" width="7" height="7" rx="1.5"></rect>
        <rect x="14" y="14" width="7" height="7" rx="1.5"></rect>
        <rect x="3" y="14" width="7" height="7" rx="1.5"></rect>
    </svg>
    <span style="font-size:1.1rem; font-weight:700; color:#f1f5f9;">Panel Kontrolli</span>
</div>
""", unsafe_allow_html=True)

MODULET = [
    "📊 Dashboard",
    "📅 Shitjet Ditore",
    "📈 Realizimi",
    "🎯 Planifikimi",
    "🔍 Mundësitë",
    "📚 Historiku",
    "🏆 Leaderboard",
    "👥 Analiza RFM",
    "🤖 Asistenti AI",
    "🗺️ Route Plan AI",
    "📥 Eksport Excel",
]

page = st.sidebar.radio("Zgjidh Modulin:", MODULET, label_visibility="collapsed")

# =========================================================
# 5. NGARKIMI I TË DHËNAVE - OPTIMIZUAR
# =========================================================
@st.cache_data(ttl=600, show_spinner="🔄 Duke ngarkuar të dhënat...")
def load_all_data():
    try:
        conn = st.connection("sql", type="sql")
        df_sql = conn.query(
            "SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht "
            "FROM dbo.GetRaportiMadhView",
            ttl=600,
        )
        df_sql.columns = df_sql.columns.str.strip()
        df_sql["Data"] = pd.to_datetime(df_sql["Data"], errors="coerce")

        df_map = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
        df_map.columns = df_map.columns.str.strip()
        df_map = df_map[["KODI", "KATEG.", "KG/SKU", "NGA LISTA E CMIMEVE"]].copy()
        df_map["KODI"] = df_map["KODI"].astype(str).str.strip()

        df = pd.merge(df_sql, df_map, left_on="KodiArt", right_on="KODI", how="left")
        df["kg"] = df["Sasia"] * df["KG/SKU"].fillna(0)
        df.rename(columns={"KATEG.": "kat", "NGA LISTA E CMIMEVE": "statusi"}, inplace=True)
        df["Vlera_Historike"] = pd.to_numeric(df["VleraRresht"], errors="coerce").fillna(0)
        df["kat"] = df["kat"].fillna("ETJ")
        df["statusi"] = df["statusi"].fillna("inaktiv")

        def klasifiko_kategorine(k):
            val = str(k).upper()
            if val == "V" or "OLIM" in val:
                return "OLIM"
            elif val == "ETJ":
                return "ETJ"
            return "DEKA"

        df["Grup_Filtri"] = df["kat"].apply(klasifiko_kategorine)
        return df
    except Exception as e:
        st.error(f"⚠️ Gabim teknik gjatë ngarkimit: {e}")
        return None


@st.cache_data(ttl=600)
def load_product_data():
    try:
        df_link = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
        df_link = df_link[["KODI", "KATEG."]].rename(
            columns={"KODI": "KodiArt", "KATEG.": "KOD KAT"}
        )
        df_names = pd.read_excel("produkte+.xlsx", sheet_name="kat_prod")
        df_names = df_names[["KOD KAT", "EMRI KAT"]]
        return df_link, df_names
    except Exception as e:
        st.warning(f"Produktet: {e}")
        return None, None


df_raw = load_all_data()
df_link, df_names = load_product_data()

if df_raw is not None and df_link is not None:
    df_raw = pd.merge(df_raw, df_link, on="KodiArt", how="left")
    if df_names is not None:
        df_raw = pd.merge(df_raw, df_names, on="KOD KAT", how="left")
        df_raw["kat"] = df_raw["EMRI KAT"].fillna(df_raw["KOD KAT"]).fillna("Pa Kategori")

# =========================================================
# 6. STATUS SQL + RIFRESKO
# =========================================================
if df_raw is not None and not df_raw.empty:
    data_maksimale = df_raw["Data"].max()
    sot_data = datetime.now().date()

    with st.sidebar.container(border=True):
        if st.button("🔄 Rifresko nga SQL Server", use_container_width=True,
                     help="Tërhiq faturat më të fundit live nga databaza."):
            st.cache_data.clear()
            st.rerun()

        if pd.notnull(data_maksimale):
            koha_fmt = data_maksimale.strftime("%d/%m/%Y %H:%M")
            if data_maksimale.date() == sot_data:
                st.markdown(f"🟢 **LIVE** · Fat. fundit: `{koha_fmt}`")
            else:
                vonesa = (sot_data - data_maksimale.date()).days
                st.markdown(f"🟡 **OK** · Fat. fundit: `{koha_fmt}` ·  {vonesa}d vonesë")

# =========================================================
# 7. LIBRARIA E PLANEVE (cache_resource për persistencë)
# =========================================================
@st.cache_resource
def merr_librarine_permanente():
    return {"Zgjedhje Manuale (Pa Ruajtje)": None}

# =========================================================
# 8. SIDEBAR - FILTRAT DHE PLANI
# =========================================================
def nderto_sidebar():
    if df_raw is None or df_raw.empty:
        st.error("⚠️ Nuk u morën të dhënat. Kontrollo lidhjen dhe secrets.toml.")
        st.stop()

    # Inicializimi i session_state
    for key, default in [
        ("start_d", df_raw["Data"].min().date()),
        ("end_d", df_raw["Data"].max().date()),
        ("rritja_val", 10),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    libraria_p = merr_librarine_permanente()
    opsionet_lib = list(libraria_p.keys())

    # Ngarko plan nga libraria
    if st.session_state.get("plan_per_te_ngarkuar"):
        emri_planit = st.session_state["plan_per_te_ngarkuar"]
        plani = libraria_p.get(emri_planit)
        if plani:
            st.session_state["start_d"] = plani["start"]
            st.session_state["end_d"] = plani["end"]
            st.session_state["rritja_val"] = plani["rritja"]
        st.session_state["plan_per_te_ngarkuar"] = None

    with st.sidebar.expander("⚙️ Vendosja e Planit", expanded=True):
        st.subheader("📂 Libraria e Planeve")

        def on_change_libraria():
            z = st.session_state["temp_selectbox_key"]
            if z != "Zgjedhje Manuale (Pa Ruajtje)":
                st.session_state["plan_per_te_ngarkuar"] = z

        st.selectbox("Thirr plan të ruajtur:", options=opsionet_lib,
                     index=0, key="temp_selectbox_key", on_change=on_change_libraria)

        date_range = st.date_input(
            "Periudha referente:",
            value=(st.session_state["start_d"], st.session_state["end_d"]),
            key="date_input_key",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state["start_d"], st.session_state["end_d"] = date_range

        rritja = st.number_input("Rritja e planit (%)", value=st.session_state["rritja_val"],
                                 key="rritja_input")
        st.session_state["rritja_val"] = rritja

        with st.expander("💾 Ruaj / Fshi Plan"):
            emri_ri = st.text_input("Emri i planit:", key="emri_ri_txt")
            if st.button("➕ Ruaj Planin", use_container_width=True):
                if emri_ri.strip():
                    libraria_p[emri_ri] = {
                        "start": st.session_state["start_d"],
                        "end": st.session_state["end_d"],
                        "rritja": st.session_state["rritja_val"],
                    }
                    st.success(f"✅ '{emri_ri}' u ruajt!")
                    st.rerun()
                else:
                    st.error("Vendos një emër!")

            plane_fshirje = [p for p in opsionet_lib if p != "Zgjedhje Manuale (Pa Ruajtje)"]
            if plane_fshirje:
                pl_fsh = st.selectbox("Fshi:", options=plane_fshirje, key="fshirje_sel_key")
                if st.button("❌ Fshi", use_container_width=True):
                    del libraria_p[pl_fsh]
                    st.warning(f"🗑️ '{pl_fsh}' u fshi!")
                    st.rerun()

    # Filtrat
    grup_sel = st.sidebar.selectbox("🗂️ Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"])
    agj_list = sorted([str(x) for x in df_raw["ForcaShitese"].unique()
                       if x not in ["nan", "None"]])
    agj_sel = st.sidebar.selectbox("👤 Filtro Agjentin:", ["Të gjithë"] + agj_list)

    k_list = (df_raw[df_raw["ForcaShitese"] == agj_sel]["Klienti"].unique()
              if agj_sel != "Të gjithë" else df_raw["Klienti"].unique())
    klientet_selected = st.sidebar.multiselect("🏪 Zgjidh Klientin:", sorted(list(k_list)))

    st.sidebar.divider()
    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

    # Info panel
    with st.sidebar.expander("ℹ️ Detajet e zgjedhjes", expanded=False):
        nr_aktiv = df_raw[df_raw["statusi"].astype(str).str.upper() == "AKTIV"]["Artikulli"].nunique()
        nr_inaktiv = df_raw[df_raw["statusi"].astype(str).str.upper() != "AKTIV"]["Artikulli"].nunique()
        start_date = st.session_state["start_d"]
        end_date = st.session_state["end_d"]
        st.write(f"📅 **Periudha:** {start_date.strftime('%d/%m/%Y')} – {end_date.strftime('%d/%m/%Y')}")
        st.write(f"📈 **Rritja:** {rritja}%")
        st.write(f"👤 **Agjenti:** {agj_sel}")
        st.write(f"🏢 **Klientë:** {len(klientet_selected) if klientet_selected else 'Të gjithë'}")
        st.write(f"📦 **Aktiv:** {nr_aktiv} | **Inaktiv:** {nr_inaktiv}")

    return st.session_state["start_d"], st.session_state["end_d"], rritja, grup_sel, agj_sel, klientet_selected


start_date, end_date, rritja, grup_sel, agj_sel, klientet_selected = nderto_sidebar()


# =========================================================
# HELPER: Filtro df_raw sipas sidebar-it
# =========================================================
def filtro_df(df, apliko_periudhen=True):
    d = df.copy()
    if apliko_periudhen:
        d = d[(d["Data"].dt.date >= start_date) & (d["Data"].dt.date <= end_date)]
    if grup_sel != "Të gjitha":
        d = d[d["Grup_Filtri"] == grup_sel]
    if agj_sel != "Të gjithë":
        d = d[d["ForcaShitese"] == agj_sel]
    if klientet_selected:
        d = d[d["Klienti"].isin(klientet_selected)]
    return d


# =========================================================
# HELPER: Eksport Excel
# =========================================================
def df_to_excel_bytes(sheets_dict):
    """sheets_dict = {"Sheet1": df1, "Sheet2": df2}"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets_dict.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


# =========================================================
# MODULI: DASHBOARD (I RI)
# =========================================================
if page == "📊 Dashboard":
    st.title("Dashboard · Pasqyra e Përgjithshme")
    sot = datetime.now()

    if df_raw is not None:
        # KPI-të kryesore
        df_muaji = df_raw[(df_raw["Data"].dt.year == sot.year) &
                          (df_raw["Data"].dt.month == sot.month)]
        if agj_sel != "Të gjithë":
            df_muaji = df_muaji[df_muaji["ForcaShitese"] == agj_sel]
        if grup_sel != "Të gjitha":
            df_muaji = df_muaji[df_muaji["Grup_Filtri"] == grup_sel]

        # Periudha referente për target
        dff_ref = filtro_df(df_raw)
        n_months = max(1, (end_date.year - start_date.year) * 12 +
                       (end_date.month - start_date.month))
        target_muaji = dff_ref["kg"].sum() / n_months * (1 + rritja / 100)

        kg_muaji = df_muaji["kg"].sum()
        vlera_muaji = df_muaji["Vlera_Historike"].sum()
        realizimi_pct = (kg_muaji / target_muaji * 100) if target_muaji > 0 else 0
        klientet_aktiv = df_muaji["Klienti"].nunique()
        cmimi_mes = vlera_muaji / kg_muaji if kg_muaji > 0 else 0

        # Muaji kaluar
        m_kal = sot.month - 1 or 12
        v_kal = sot.year if sot.month > 1 else sot.year - 1
        df_mk = df_raw[(df_raw["Data"].dt.year == v_kal) & (df_raw["Data"].dt.month == m_kal)]
        if agj_sel != "Të gjithë":
            df_mk = df_mk[df_mk["ForcaShitese"] == agj_sel]
        kg_mk = df_mk["kg"].sum()
        delta_mk = ((kg_muaji / kg_mk) - 1) * 100 if kg_mk > 0 else 0

        # Row 1 - KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🎯 Target Muajit", f"{target_muaji:,.0f} kg")
        c2.metric("📦 Realizuar", f"{kg_muaji:,.0f} kg",
                  delta=f"{realizimi_pct:.1f}% i planit")
        c3.metric("💰 Vlera (L)", f"{vlera_muaji:,.0f}",
                  delta=f"{delta_mk:+.1f}% vs muajit kaluar")
        c4.metric("👥 Klientë Aktivë", f"{klientet_aktiv}")
        c5.metric("⚖️ Çmim Mes./kg", f"{cmimi_mes:,.1f} L")

        st.divider()

        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.subheader("📈 Shitjet Mujore (12 muajt e fundit)")
            df_trend = df_raw.copy()
            if agj_sel != "Të gjithë":
                df_trend = df_trend[df_trend["ForcaShitese"] == agj_sel]
            if grup_sel != "Të gjitha":
                df_trend = df_trend[df_trend["Grup_Filtri"] == grup_sel]
            df_trend["YM"] = df_trend["Data"].dt.to_period("M")
            trend_data = df_trend.groupby("YM")["kg"].sum().reset_index()
            trend_data = trend_data.tail(12)
            trend_data["YM_str"] = trend_data["YM"].astype(str)

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=trend_data["YM_str"], y=trend_data["kg"],
                marker=dict(
                    color=trend_data["kg"],
                    colorscale=[[0, "#bfdbfe"], [1, "#1d4ed8"]],
                    showscale=False,
                ),
                hovertemplate="%{x}<br>%{y:,.0f} kg<extra></extra>",
            ))
            fig_trend.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                height=280, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        with col_r:
            st.subheader("🗂️ Shpërndarja sipas Grupeve")
            df_grp = filtro_df(df_raw)
            grp_data = df_grp.groupby("Grup_Filtri")["kg"].sum().reset_index()
            fig_pie = px.pie(
                grp_data, values="kg", names="Grup_Filtri",
                color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b"],
                hole=0.45,
            )
            fig_pie.update_layout(
                height=280, margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True, legend=dict(orientation="h", y=-0.1),
            )
            fig_pie.update_traces(hovertemplate="%{label}<br>%{value:,.0f} kg<extra></extra>")
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🏆 Top 10 Klientët (KG)")
            top_kl = (filtro_df(df_raw).groupby("Klienti")["kg"].sum()
                      .sort_values(ascending=False).head(10).reset_index())
            fig_kl = px.bar(
                top_kl, x="kg", y="Klienti", orientation="h",
                color="kg", color_continuous_scale=["#bfdbfe", "#1d4ed8"],
            )
            fig_kl.update_layout(
                height=320, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0, r=0, t=10, b=0),
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_kl, use_container_width=True)

        with col_b:
            st.subheader("📦 Top 10 Artikujt (KG)")
            top_art = (filtro_df(df_raw).groupby("Artikulli")["kg"].sum()
                       .sort_values(ascending=False).head(10).reset_index())
            fig_art = px.bar(
                top_art, x="kg", y="Artikulli", orientation="h",
                color="kg", color_continuous_scale=["#d1fae5", "#065f46"],
            )
            fig_art.update_layout(
                height=320, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(l=0, r=0, t=10, b=0),
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_art, use_container_width=True)


# =========================================================
# MODULI: SHITJET DITORE
# =========================================================
elif page == "📅 Shitjet Ditore":
    import calendar as cal_mod

    sot = datetime.now()  # ✅ FIX: Nuk është më hardcoded

    st.title("Shitjet Ditore")
    st.markdown(
        f"<h3 style='color:#1e40af; margin-top:-15px; border:none;'>"
        f"Muaji: {muajt_sq.get(sot.month)} {sot.year} · 👤 {agj_sel}</h3>",
        unsafe_allow_html=True,
    )
    st.divider()

    if df_raw is not None and not df_raw.empty:
        vit_aktual = sot.year
        muaj_aktual = sot.month
        para_muaj = muaj_aktual - 1 or 12
        vit_para_muaj = vit_aktual if muaj_aktual > 1 else vit_aktual - 1
        vit_para_vit = vit_aktual - 1

        emri_muaj_aktual = f"{muajt_sq.get(muaj_aktual).upper()} {vit_aktual}"
        emri_muaj_kaluar = f"{muajt_sq.get(para_muaj).upper()} {vit_para_muaj}"
        emri_vit_kaluar = f"{muajt_sq.get(muaj_aktual).upper()} {vit_para_vit}"

        df_base = df_raw.copy()
        if grup_sel != "Të gjitha":
            df_base = df_base[df_base["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_base = df_base[df_base["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_base = df_base[df_base["Klienti"].isin(klientet_selected)]

        def merr_ditore(df, vit, muaj):
            dp = df[(df["Data"].dt.year == vit) & (df["Data"].dt.month == muaj)].copy()
            if not dp.empty:
                dp["Dita"] = dp["Data"].dt.day
                return dp.groupby("Dita")["kg"].sum().to_dict()
            return {}

        data_akt = merr_ditore(df_base, vit_aktual, muaj_aktual)
        data_pm = merr_ditore(df_base, vit_para_muaj, para_muaj)
        data_pv = merr_ditore(df_base, vit_para_vit, muaj_aktual)

        _, n_diteve = cal_mod.monthrange(vit_aktual, muaj_aktual)
        ditet = list(range(1, n_diteve + 1))

        def kaskada(d_dict):
            baza, vlera = [], []
            kum = 0.0
            for d in range(1, n_diteve + 1):
                v = d_dict.get(d, 0.0)
                baza.append(kum)
                vlera.append(v)
                kum += v
            return baza, vlera

        b_akt, y_akt = kaskada(data_akt)
        b_pm, y_pm = kaskada(data_pm)
        b_pv, y_pv = kaskada(data_pv)

        tot_akt = sum(y_akt)
        tot_pm = sum(y_pm)
        tot_pv = sum(y_pv)
        delta_pm = ((tot_akt / tot_pm) - 1) * 100 if tot_pm > 0 else 0
        delta_pv = ((tot_akt / tot_pv) - 1) * 100 if tot_pv > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric(f"📊 {emri_muaj_aktual}", f"{tot_akt:,.0f} kg")
        c2.metric(f"vs {emri_muaj_kaluar}", f"{tot_pm:,.0f} kg", f"{delta_pm:+.1f}%")
        c3.metric(f"vs {emri_vit_kaluar}", f"{tot_pv:,.0f} kg", f"{delta_pv:+.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=ditet, y=y_pv, base=b_pv, name=emri_vit_kaluar,
                             width=0.6, marker_color="rgba(141,211,199,0.5)",
                             hovertemplate="%{y:,.0f} kg<extra></extra>"))
        fig.add_trace(go.Bar(x=ditet, y=y_pm, base=b_pm, name=emri_muaj_kaluar,
                             width=0.6, marker_color="rgba(0,105,92,0.5)",
                             hovertemplate="%{y:,.0f} kg<extra></extra>"))
        fig.add_trace(go.Bar(x=ditet, y=y_akt, base=b_akt, name=emri_muaj_aktual,
                             width=0.6, marker_color="rgba(255,193,7,0.75)",
                             text=[f"{v:,.0f}" if v > 0 else "" for v in y_akt],
                             textposition="outside",
                             hovertemplate="%{y:,.0f} kg<extra></extra>"))
        fig.update_layout(
            title=f"KASKADA KRAHASUESE · {emri_muaj_aktual}",
            barmode="overlay", plot_bgcolor="#f8fafc",
            height=600,
            xaxis=dict(title="Ditët", tickmode="array", tickvals=ditet,
                       ticktext=[f"{d:02d}" for d in ditet], range=[0.4, n_diteve + 0.6]),
            yaxis=dict(title="kg", gridcolor="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Tabela krahasuese"):
            tabela_df = pd.DataFrame({
                "Dita": [f"{d:02d}" for d in ditet],
                f"{emri_muaj_aktual} (kg)": y_akt,
                f"{emri_muaj_kaluar} (kg)": y_pm,
                f"{emri_vit_kaluar} (kg)": y_pv,
            })
            st.dataframe(
                tabela_df.style.format({
                    f"{emri_muaj_aktual} (kg)": "{:,.0f}",
                    f"{emri_muaj_kaluar} (kg)": "{:,.0f}",
                    f"{emri_vit_kaluar} (kg)": "{:,.0f}",
                }),
                use_container_width=True, hide_index=True,
            )


# =========================================================
# MODULI: REALIZIMI
# =========================================================
elif page == "📈 Realizimi":
    sot = datetime.now()
    st.title(f"Realizimi Live · {muajt_sq.get(sot.month)} {sot.year}")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if df_raw is not None:
        dff_ref = filtro_df(df_raw)
        n_months_ref = max(1, (end_date.year - start_date.year) * 12 +
                           (end_date.month - start_date.month))
        rritja_faktori = 1 + rritja / 100

        gp_target_cat = dff_ref.groupby("kat").agg({"kg": "sum"}).reset_index()
        gp_target_cat["KG_Target"] = (gp_target_cat["kg"] / n_months_ref) * rritja_faktori
        t_target = gp_target_cat["KG_Target"].sum()

        df_live = df_raw[(df_raw["Data"].dt.year == sot.year) &
                         (df_raw["Data"].dt.month == sot.month)].copy()
        if grup_sel != "Të gjitha":
            df_live = df_live[df_live["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_live = df_live[df_live["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_live = df_live[df_live["Klienti"].isin(klientet_selected)]

        t_real = df_live["kg"].sum()
        t_vlera_live = df_live["Vlera_Historike"].sum()
        cmimi_mesatar = t_vlera_live / t_real if t_real > 0 else 0

        # Ditët pune
        start_muaji = sot.replace(day=1)
        fund_muaji = start_muaji + pd.offsets.MonthEnd(0)
        ditet_deri_sot = len([d for d in pd.date_range(start_muaji, sot) if d.weekday() < 6])
        ditet_totale = len([d for d in pd.date_range(start_muaji, fund_muaji) if d.weekday() < 6])
        koha_perq = (ditet_deri_sot / ditet_totale * 100) if ditet_totale > 0 else 0
        total_perc = (t_real / t_target * 100) if t_target > 0 else 0

        c1, c2, c5, c3, c4 = st.columns(5)
        c1.metric("🎯 Target KG", f"{t_target:,.0f}")
        c2.metric("📦 Realizuar KG", f"{t_real:,.0f}")
        c3.metric("📊 Realizimi %", f"{total_perc:.1f}%",
                  delta=f"{total_perc - koha_perq:.1f}% vs Koha",
                  delta_color="normal" if total_perc >= koha_perq else "inverse")
        c4.metric("📅 Ditë Pune", f"{ditet_deri_sot}/{ditet_totale}", f"{koha_perq:.1f}% e muajit")
        c5.metric("⚖️ Çmimi Mes./kg", f"{cmimi_mesatar:,.1f} L")

        # Progress bar vizuale
        prog_color = "#10b981" if total_perc >= koha_perq else "#ef4444"
        st.markdown(f"""
        <div style="background:#f1f5f9; border-radius:8px; height:16px; margin:8px 0 16px 0; overflow:hidden;">
            <div style="background:{prog_color}; width:{min(total_perc,100):.1f}%; height:100%; border-radius:8px;
                        transition:width 0.5s; display:flex; align-items:center; justify-content:flex-end;
                        padding-right:8px; font-size:11px; color:white; font-weight:600;">
                {total_perc:.1f}%
            </div>
        </div>
        <div style="background:#e2e8f0; width:{koha_perq:.1f}%; height:3px; border-radius:2px; margin-bottom:16px;"></div>
        """, unsafe_allow_html=True)

        st.divider()

        # Trendët
        st.subheader("🔍 Analiza e Trendeve")
        tr1, tr2, tr3 = st.columns(3)

        ritmi = t_real / ditet_deri_sot if ditet_deri_sot > 0 else 0
        projeksioni = ritmi * ditet_totale
        tr1.metric("📈 Trendi Linear", f"{projeksioni:,.0f} kg",
                   delta=f"{projeksioni - t_target:,.0f} vs Plani")

        m_kaluar = sot - pd.DateOffset(months=1)
        mask_mk = ((df_raw["Data"].dt.year == m_kaluar.year) &
                   (df_raw["Data"].dt.month == m_kaluar.month) &
                   (df_raw["Data"].dt.day <= sot.day))
        df_mk = df_raw[mask_mk].copy()
        if grup_sel != "Të gjitha": df_mk = df_mk[df_mk["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë": df_mk = df_mk[df_mk["ForcaShitese"] == agj_sel]
        t_mk = df_mk["kg"].sum()
        rritja_m = ((t_real / t_mk) - 1) * 100 if t_mk > 0 else 0
        tr2.metric("vs Muaji Kaluar", f"{t_mk:,.0f} kg", delta=f"{rritja_m:.1f}%")

        mask_vk = ((df_raw["Data"].dt.year == sot.year - 1) &
                   (df_raw["Data"].dt.month == sot.month) &
                   (df_raw["Data"].dt.day <= sot.day))
        df_vk = df_raw[mask_vk].copy()
        if grup_sel != "Të gjitha": df_vk = df_vk[df_vk["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë": df_vk = df_vk[df_vk["ForcaShitese"] == agj_sel]
        t_vk = df_vk["kg"].sum()
        rritja_v = ((t_real / t_vk) - 1) * 100 if t_vk > 0 else 0
        tr3.metric("vs Viti Kaluar", f"{t_vk:,.0f} kg", delta=f"{rritja_v:.1f}%")

        st.divider()

        # Tabet Kategori / Agjentë / Klientë
        df_comp = gp_target_cat.copy()
        df_comp = pd.merge(
            df_comp[["kat", "KG_Target"]],
            df_live.groupby("kat", as_index=False).agg(KG_Real=("kg", "sum")),
            on="kat", how="left",
        ).fillna(0)

        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        with t1:
            df_comp["Progresi"] = (df_comp["KG_Real"] / df_comp["KG_Target"] * 100).clip(upper=100)
            st.dataframe(df_comp[["kat", "KG_Target", "KG_Real", "Progresi"]],
                column_config={
                    "kat": "Kategoria",
                    "KG_Target": st.column_config.NumberColumn("Target (KG)", format="%d"),
                    "KG_Real": st.column_config.NumberColumn("Realizuar (KG)", format="%d"),
                    "Progresi": st.column_config.ProgressColumn("Ecuria %", min_value=0, max_value=100, format="%.1f%%"),
                }, hide_index=True, use_container_width=True)

        with t2:
            gp_agj_t = dff_ref.groupby("ForcaShitese").agg({"kg": "sum"}).reset_index()
            gp_agj_t["Target_AGJ"] = (gp_agj_t["kg"] / n_months_ref) * rritja_faktori
            gp_agj_l = df_live.groupby("ForcaShitese").agg({"kg": "sum"}).reset_index().rename(columns={"kg": "Real_AGJ"})
            df_agj = pd.merge(gp_agj_t[["ForcaShitese", "Target_AGJ"]], gp_agj_l, on="ForcaShitese", how="left").fillna(0)
            df_agj["%"] = (df_agj["Real_AGJ"] / df_agj["Target_AGJ"] * 100).clip(upper=100)
            st.dataframe(df_agj.sort_values("%", ascending=False),
                column_config={
                    "ForcaShitese": "Agjenti",
                    "Target_AGJ": st.column_config.NumberColumn("Target", format="%d"),
                    "Real_AGJ": st.column_config.NumberColumn("Realizuar", format="%d"),
                    "%": st.column_config.ProgressColumn("Ecuria", min_value=0, max_value=100, format="%.1f%%"),
                }, hide_index=True, use_container_width=True)

        with t3:
            gp_kl_t = dff_ref.groupby(["Klienti", "ForcaShitese"]).agg({"kg": "sum"}).reset_index()
            gp_kl_t["Target_KL"] = (gp_kl_t["kg"] / n_months_ref) * rritja_faktori
            gp_kl_l = df_live.groupby("Klienti").agg({"kg": "sum"}).reset_index().rename(columns={"kg": "Real_KL"})
            df_kl2 = pd.merge(gp_kl_t[["Klienti", "ForcaShitese", "Target_KL"]], gp_kl_l, on="Klienti", how="left").fillna(0)
            df_kl2["%"] = (df_kl2["Real_KL"] / df_kl2["Target_KL"] * 100).clip(upper=100)
            df_kl2 = df_kl2[df_kl2["Target_KL"] > 0]
            st.dataframe(df_kl2.sort_values("%", ascending=False),
                column_config={
                    "Klienti": "Klienti", "ForcaShitese": "Agjenti",
                    "Target_KL": st.column_config.NumberColumn("Target", format="%d"),
                    "Real_KL": st.column_config.NumberColumn("Realizuar", format="%d"),
                    "%": st.column_config.ProgressColumn("Ecuria", min_value=0, max_value=100, format="%.1f%%"),
                }, hide_index=True, use_container_width=True)

        st.divider()

        # Eksport HTML Raport
        agj_emri = agj_sel.replace(" ", "_") if agj_sel != "Të gjithë" else "Gjithe"
        klientet_text = ", ".join(klientet_selected) if klientet_selected else "Të gjithë"
        html_report = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>body{{font-family:'Segoe UI',sans-serif;margin:30px;background:#f8f9fa;color:#333}}
        .header{{background:linear-gradient(135deg,#1a237e,#3949ab);color:white;padding:25px;border-radius:12px;text-align:center}}
        .stats{{display:flex;gap:15px;margin:20px 0}}.stat{{background:white;padding:20px;border-radius:10px;border-bottom:4px solid #3949ab;flex:1;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.08)}}
        .stat h3{{margin:0;font-size:11px;text-transform:uppercase;color:#777;letter-spacing:1px}}.stat p{{font-size:22px;font-weight:700;color:#1a237e;margin:8px 0}}
        table{{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.08)}}
        th,td{{padding:12px 15px;text-align:left;border-bottom:1px solid #eee}}th{{background:#f1f5f9;font-weight:600;color:#555}}
        .pos{{color:#2e7d32;font-weight:700}}.neg{{color:#c62828;font-weight:700}}
        .footer{{text-align:center;margin-top:30px;font-size:11px;color:#999;padding-top:15px;border-top:1px solid #eee}}</style>
        </head><body>
        <div class="header"><h1 style="margin:0">Realizimi: {muajt_sq.get(sot.month)} {sot.year}</h1>
        <p style="opacity:0.8;margin:8px 0 0">Agjenti: {agj_sel} · Grupi: {grup_sel} · Klientët: {klientet_text}</p></div>
        <div class="stats">
          <div class="stat"><h3>Target</h3><p>{t_target:,.0f} kg</p></div>
          <div class="stat"><h3>Realizuar</h3><p>{t_real:,.0f} kg</p></div>
          <div class="stat"><h3>Ecuria</h3><p>{total_perc:.1f}%</p></div>
          <div class="stat"><h3>Ditë Pune</h3><p>{ditet_deri_sot}/{ditet_totale}</p></div>
          <div class="stat"><h3>Çmim Mes.</h3><p>{cmimi_mesatar:,.1f} L</p></div>
        </div>
        <h2>Krahasimi i Trendeve</h2>
        <table><thead><tr><th>Lloji</th><th>Vlera</th><th>Devijimi</th></tr></thead><tbody>
        <tr><td><strong>Trendi Linear</strong></td><td>{projeksioni:,.0f} kg</td>
            <td class="{'pos' if projeksioni>=t_target else 'neg'}">{projeksioni-t_target:,.0f} kg vs Plan</td></tr>
        <tr><td><strong>vs Muaji Kaluar</strong></td><td>{t_mk:,.0f} kg</td>
            <td class="{'pos' if rritja_m>=0 else 'neg'}">{rritja_m:+.1f}%</td></tr>
        <tr><td><strong>vs Viti Kaluar</strong></td><td>{t_vk:,.0f} kg</td>
            <td class="{'pos' if rritja_v>=0 else 'neg'}">{rritja_v:+.1f}%</td></tr>
        </tbody></table>
        <div class="footer">Gjeneruar: {sot.strftime('%d/%m/%Y %H:%M')} · DEKA SQL v4.0</div>
        </body></html>"""

        st.download_button(
            label=f"💾 Shkarko Raportin HTML · {agj_emri}_{sot.strftime('%d_%m_%Y')}.html",
            data=html_report,
            file_name=f"Raport_{agj_emri}_{sot.strftime('%d_%m_%Y')}.html",
            mime="text/html", use_container_width=True,
        )


# =========================================================
# MODULI: PLANIFIKIMI
# =========================================================
elif page == "🎯 Planifikimi" and df_raw is not None:
    sot = datetime.now()
    st.title(f"Plani: {muajt_sq.get(sot.month)} {sot.year}")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    data_fundit_db = df_raw["Data"].max().strftime("%d/%m/%Y")
    st.info(f"🔄 Update i fundit: **{data_fundit_db}** | Grupi: **{grup_sel}**")

    # Çmimi i fundit (pa muajin korrent)
    mask_past = (df_raw["Data"].dt.year < sot.year) | (
        (df_raw["Data"].dt.year == sot.year) & (df_raw["Data"].dt.month < sot.month))
    df_past = df_raw[mask_past].copy()
    df_past["Cmimi_Rresht"] = df_past["Vlera_Historike"] / df_past["kg"].replace(0, 1)
    last_prices = (df_past.sort_values("Data").drop_duplicates("KodiArt", keep="last")
                   [["KodiArt", "Cmimi_Rresht"]].rename(columns={"Cmimi_Rresht": "Cmimi_Fundit"}))

    dff = filtro_df(df_raw)
    n_months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month))

    st.session_state["start_d_plani"] = start_date
    st.session_state["end_d_plani"] = end_date
    st.session_state["rritja_plani"] = rritja
    st.session_state["grup_plani"] = grup_sel

    gp = (dff.groupby(["ForcaShitese", "Klienti", "kat", "KodiArt", "Artikulli"])
          .agg({"kg": "sum", "Vlera_Historike": "sum"}).reset_index())
    gp["Cmimi_Mes"] = gp["Vlera_Historike"] / gp["kg"].replace(0, 1)
    gp = gp.merge(last_prices, on="KodiArt", how="left")
    gp["Plani_KG"] = (gp["kg"] / n_months) * (1 + rritja / 100)
    gp["Vlera_Planifikuar"] = gp["Plani_KG"] * gp["Cmimi_Fundit"].fillna(gp["Cmimi_Mes"])

    t_kg_ref = gp["kg"].sum()
    t_v_ref = gp["Vlera_Historike"].sum()
    t_kg_plan = gp["Plani_KG"].sum()
    t_v_plan = gp["Vlera_Planifikuar"].sum()
    cm_ref = t_v_ref / t_kg_ref if t_kg_ref > 0 else 0
    cm_plan = t_v_plan / t_kg_plan if t_kg_plan > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Plani KG", f"{t_kg_plan:,.0f}")
    c2.metric("⚖️ Çmimi Mes. Periudhës", f"{cm_ref:,.1f} L/kg")
    c3.metric("⚖️ Çmimi Fundit Mes.", f"{cm_plan:,.1f} L/kg", f"{cm_plan-cm_ref:,.1f} L")
    c4.metric("💰 Vlera Totale Plani", f"{t_v_plan:,.0f} L")

    col_cfg = {
        "Cmimi_Mes": st.column_config.NumberColumn("Çmimi Mes. Periudhës", format="%.1f L"),
        "Cmimi_Fundit": st.column_config.NumberColumn("Çmimi i Fundit", format="%.1f L"),
        "Plani_KG": st.column_config.NumberColumn("Plani KG", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d"),
    }

    st.divider()

    if klientet_selected:
        st.subheader("📍 Detajet Artikujve")
        st.dataframe(gp[["Klienti", "kat", "Artikulli", "Cmimi_Mes", "Cmimi_Fundit",
                          "Plani_KG", "Vlera_Planifikuar"]],
                     hide_index=True, column_config=col_cfg, use_container_width=True)
    else:
        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])
        with t1:
            df_k = gp.groupby("kat").agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum",
                                           "kg": "sum", "Vlera_Historike": "sum"}).reset_index()
            df_k["Cmimi_Mes"] = df_k["Vlera_Historike"] / df_k["kg"].replace(0, 1)
            df_k["Cmimi_Fundit"] = df_k["Vlera_Planifikuar"] / df_k["Plani_KG"].replace(0, 1)
            st.dataframe(df_k[["kat", "Cmimi_Mes", "Cmimi_Fundit", "Plani_KG", "Vlera_Planifikuar"]]
                         .sort_values("Plani_KG", ascending=False),
                         hide_index=True, column_config=col_cfg, use_container_width=True)
        with t2:
            df_a = gp.groupby("ForcaShitese").agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum",
                                                     "kg": "sum", "Vlera_Historike": "sum"}).reset_index()
            df_a["Cmimi_Mes"] = df_a["Vlera_Historike"] / df_a["kg"].replace(0, 1)
            df_a["Cmimi_Fundit"] = df_a["Vlera_Planifikuar"] / df_a["Plani_KG"].replace(0, 1)
            st.dataframe(df_a[["ForcaShitese", "Cmimi_Mes", "Cmimi_Fundit", "Plani_KG", "Vlera_Planifikuar"]]
                         .sort_values("Plani_KG", ascending=False),
                         hide_index=True, column_config=col_cfg, use_container_width=True)
        with t3:
            df_kl = gp.groupby(["Klienti", "ForcaShitese"]).agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum",
                                                                    "kg": "sum", "Vlera_Historike": "sum"}).reset_index()
            df_kl["Cmimi_Mes"] = df_kl["Vlera_Historike"] / df_kl["kg"].replace(0, 1)
            df_kl["Cmimi_Fundit"] = df_kl["Vlera_Planifikuar"] / df_kl["Plani_KG"].replace(0, 1)
            st.dataframe(df_kl[["Klienti", "ForcaShitese", "Cmimi_Mes", "Cmimi_Fundit", "Plani_KG", "Vlera_Planifikuar"]]
                         .sort_values("Plani_KG", ascending=False),
                         hide_index=True, column_config=col_cfg, use_container_width=True)

    # Eksport HTML plan
    if st.sidebar.button("📄 Gjenero Raportin HTML"):
        html = "<html><head><style>body{font-family:sans-serif}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ddd;padding:8px}th{background:#f2f2f2}</style></head><body>"
        html += f"<h1>Raporti i Planit ({grup_sel})</h1>"
        for agjent in sorted(gp["ForcaShitese"].unique()):
            html += f"<h3>{agjent}</h3><table><thead><tr><th>Kategoria</th><th>Plani KG</th><th>Vlera</th></tr></thead><tbody>"
            for _, r in gp[gp["ForcaShitese"] == agjent].groupby("kat").agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum"}).reset_index().iterrows():
                html += f"<tr><td>{r['kat']}</td><td>{r['Plani_KG']:,.0f}</td><td>{r['Vlera_Planifikuar']:,.0f} L</td></tr>"
            html += "</tbody></table><br>"
        html += "</body></html>"
        b64 = base64.b64encode(html.encode()).decode()
        st.sidebar.markdown(
            f'<a href="data:text/html;base64,{b64}" download="Plani.html" '
            f'style="padding:10px;background:#2563eb;color:white;text-decoration:none;border-radius:6px;">📥 Shkarko HTML</a>',
            unsafe_allow_html=True,
        )


# =========================================================
# MODULI: MUNDËSITË
# =========================================================
elif page == "🔍 Mundësitë":
    st.title("Analiza e Mundësive (Gap Analysis)")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    with st.expander("ℹ️ Metodologjia"):
        st.write("""**Gap Analysis** identifikon artikujt që klienti i ka blerë historikisht
        por nuk i ka blerë në 90 ditët e fundit. Renditja bëhet sipas KG Historike.""")

    if df_raw is not None:
        df_m = df_raw[df_raw["statusi"].astype(str).str.upper() == "AKTIV"].copy()
        if agj_sel != "Të gjithë": df_m = df_m[df_m["ForcaShitese"] == agj_sel]
        if klientet_selected: df_m = df_m[df_m["Klienti"].isin(klientet_selected)]
        if grup_sel != "Të gjitha": df_m = df_m[df_m["Grup_Filtri"] == grup_sel]

        sot = datetime.now()
        kufiri = sot - pd.Timedelta(days=90)
        sh_hist = df_m[df_m["Data"] < kufiri]
        sh_akt = df_m[df_m["Data"] >= kufiri]

        portfolio_hist = (sh_hist.groupby(["Klienti", "Artikulli", "kat"])
                          .agg({"Data": "max", "kg": "sum"}).reset_index())
        portfolio_akt = sh_akt[["Klienti", "Artikulli"]].drop_duplicates()
        portfolio_akt["Blerë"] = True

        mundesite = pd.merge(portfolio_hist, portfolio_akt, on=["Klienti", "Artikulli"], how="left")
        mundesite = mundesite[mundesite["Blerë"].isna()].copy()

        if not mundesite.empty:
            mundesite["Blerja e Fundit"] = mundesite["Data"].dt.strftime("%d/%m/%Y")
            tabela = mundesite[["Klienti", "Artikulli", "kat", "Blerja e Fundit", "kg"]].copy()
            tabela.columns = ["Klienti", "Artikulli", "Kategoria", "Blerja e Fundit", "KG Historike"]

            c1, c2, c3 = st.columns(3)
            c1.metric("⚠️ Raste të gjetura", len(tabela))
            c2.metric("🏪 Klientë me gap", tabela["Klienti"].nunique())
            c3.metric("📦 Artikuj të harruar", tabela["Artikulli"].nunique())

            st.subheader(f"⚠️ {len(tabela)} mundësi potenciale")
            st.dataframe(tabela.sort_values("KG Historike", ascending=False),
                         use_container_width=True, height=500, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                top_k = tabela.groupby("Klienti")["KG Historike"].sum().idxmax()
                st.metric("🏆 Klienti me më shumë potencial", top_k)
            with c2:
                top_a = tabela.groupby("Artikulli")["KG Historike"].sum().idxmax()
                st.metric("📦 Artikulli më i harruar", top_a)

            csv = tabela.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Shkarko CSV", csv, "mundesite_gap.csv", "text/csv")
        else:
            st.success("✅ Nuk u gjet asnjë gap!")


# =========================================================
# MODULI: HISTORIKU
# =========================================================
elif page == "📚 Historiku":
    st.title("Historiku i Shitjeve & Analiza e Artikujve")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if df_raw is not None:
        df_hist = df_raw.copy()
        df_hist["Viti"] = df_hist["Data"].dt.year
        df_hist["Muaji"] = df_hist["Data"].dt.month

        if agj_sel != "Të gjithë": df_hist = df_hist[df_hist["ForcaShitese"] == agj_sel]
        if klientet_selected: df_hist = df_hist[df_hist["Klienti"].isin(klientet_selected)]
        if grup_sel != "Të gjitha": df_hist = df_hist[df_hist["Grup_Filtri"] == grup_sel]

        st.subheader("🔍 Filtra shtesë")
        c1, c2 = st.columns(2)
        with c1:
            vitet = sorted(df_hist["Viti"].unique(), reverse=True)
            viti_sel = st.multiselect("Krahaso Vitet:", vitet, default=vitet[:2])
        with c2:
            kat_list = sorted(df_hist["kat"].unique())
            kat_sel = st.multiselect("Filtro Kategoritë:", kat_list, default=kat_list)

        df_final = df_hist[df_hist["Viti"].isin(viti_sel) & df_hist["kat"].isin(kat_sel)]

        st.subheader("📈 Trendi Mujor (KG)")
        chart_data = df_final.groupby(["Viti", "Muaji"])["kg"].sum().reset_index()
        if not chart_data.empty:
            chart_pivot = chart_data.pivot(index="Muaji", columns="Viti", values="kg").fillna(0)
            chart_pivot.index = [muajt_sq.get(m, m) for m in chart_pivot.index]
            st.line_chart(chart_pivot)

        st.divider()
        st.subheader("🏆 Lista e Plotë e Artikujve")
        tabela_art = (df_final.groupby(["Artikulli", "kat"])
                      .agg({"kg": "sum", "Vlera_Historike": "sum", "Klienti": "nunique"})
                      .rename(columns={"kg": "Totale KG", "Vlera_Historike": "Vlera (L)", "Klienti": "Nr. Klientëve"})
                      .sort_values("Totale KG", ascending=False))
        st.dataframe(
            tabela_art.style.format({"Totale KG": "{:,.1f}", "Vlera (L)": "{:,.0f}", "Nr. Klientëve": "{:,.0f}"}),
            use_container_width=True, height=600,
        )
        csv = tabela_art.to_csv().encode("utf-8")
        st.download_button("📥 Shkarko CSV", csv, "historiku_artikujve.csv", "text/csv")


# =========================================================
# MODULI: LEADERBOARD (I RI)
# =========================================================
elif page == "🏆 Leaderboard":
    st.title("Leaderboard · Krahasimi i Agjentëve")
    sot = datetime.now()

    if df_raw is not None:
        # Periudha për target
        dff_ref = filtro_df(df_raw)
        n_months = max(1, (end_date.year - start_date.year) * 12 +
                       (end_date.month - start_date.month))

        # Target për agjent
        target_agj = (dff_ref.groupby("ForcaShitese")["kg"].sum().reset_index()
                      .rename(columns={"kg": "KG_Ref"}))
        target_agj["Target_Muaj"] = (target_agj["KG_Ref"] / n_months) * (1 + rritja / 100)

        # Realizimi muajit korrent
        df_live = df_raw[(df_raw["Data"].dt.year == sot.year) &
                         (df_raw["Data"].dt.month == sot.month)].copy()
        if grup_sel != "Të gjitha":
            df_live = df_live[df_live["Grup_Filtri"] == grup_sel]

        real_agj = (df_live.groupby("ForcaShitese")["kg"].sum().reset_index()
                    .rename(columns={"kg": "KG_Real"}))
        vlera_agj = (df_live.groupby("ForcaShitese")["Vlera_Historike"].sum().reset_index())

        lb = pd.merge(target_agj, real_agj, on="ForcaShitese", how="left").fillna(0)
        lb = pd.merge(lb, vlera_agj, on="ForcaShitese", how="left").fillna(0)
        lb["Ecuria_%"] = (lb["KG_Real"] / lb["Target_Muaj"] * 100).clip(lower=0)
        lb["Cmim_Mes"] = lb.apply(lambda r: r["Vlera_Historike"] / r["KG_Real"] if r["KG_Real"] > 0 else 0, axis=1)
        lb = lb.sort_values("Ecuria_%", ascending=False).reset_index(drop=True)

        # Top 3 me podium
        st.subheader(f"🥇 Renditja · {muajt_sq.get(sot.month)} {sot.year}")
        if len(lb) >= 3:
            medals = ["🥇", "🥈", "🥉"]
            css_classes = ["rank-1", "rank-2", "rank-3"]
            cols = st.columns(3)
            for i, (col, medal, css) in enumerate(zip(cols, medals, css_classes)):
                if i < len(lb):
                    row = lb.iloc[i]
                    with col:
                        st.markdown(f"""
                        <div class="{css}">
                            <div style="font-size:2rem; text-align:center">{medal}</div>
                            <div style="font-weight:700; font-size:1.05rem; text-align:center; margin:4px 0">{row['ForcaShitese']}</div>
                            <div style="font-size:0.8rem; text-align:center; color:#475569">{row['Ecuria_%']:.1f}% i planit</div>
                            <div style="font-size:1.2rem; font-weight:700; text-align:center; margin:6px 0">{row['KG_Real']:,.0f} kg</div>
                            <div style="font-size:0.75rem; text-align:center; color:#64748b">Target: {row['Target_Muaj']:,.0f} kg</div>
                        </div>
                        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 Tabela e Plotë")
        lb_display = lb.copy()
        lb_display.insert(0, "Vendi", [f"#{i+1}" for i in range(len(lb_display))])
        st.dataframe(
            lb_display[["Vendi", "ForcaShitese", "Target_Muaj", "KG_Real", "Ecuria_%", "Vlera_Historike", "Cmim_Mes"]],
            column_config={
                "Vendi": "🏅",
                "ForcaShitese": "Agjenti",
                "Target_Muaj": st.column_config.NumberColumn("Target (KG)", format="%d"),
                "KG_Real": st.column_config.NumberColumn("Realizuar (KG)", format="%d"),
                "Ecuria_%": st.column_config.ProgressColumn("Ecuria %", min_value=0, max_value=100, format="%.1f%%"),
                "Vlera_Historike": st.column_config.NumberColumn("Vlera (L)", format="%d"),
                "Cmim_Mes": st.column_config.NumberColumn("Çmim Mes. (L/kg)", format="%.1f"),
            },
            hide_index=True, use_container_width=True,
        )

        st.divider()
        st.subheader("📈 Grafiku i Krahasimit")
        fig_lb = go.Figure()
        fig_lb.add_trace(go.Bar(
            name="Target", x=lb["ForcaShitese"], y=lb["Target_Muaj"],
            marker_color="#bfdbfe", text=lb["Target_Muaj"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
        ))
        fig_lb.add_trace(go.Bar(
            name="Realizuar", x=lb["ForcaShitese"], y=lb["KG_Real"],
            marker_color="#2563eb", text=lb["KG_Real"].apply(lambda v: f"{v:,.0f}"),
            textposition="outside",
        ))
        fig_lb.update_layout(
            barmode="group", plot_bgcolor="white", paper_bgcolor="white",
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(gridcolor="#f1f5f9"),
            legend=dict(orientation="h", y=1.05),
        )
        st.plotly_chart(fig_lb, use_container_width=True)


# =========================================================
# MODULI: ANALIZA RFM (I RI)
# =========================================================
elif page == "👥 Analiza RFM":
    st.title("Analiza RFM · Segmentimi i Klientëve")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    with st.expander("ℹ️ Çfarë është RFM?"):
        st.write("""
        **RFM** është metoda kryesore e segmentimit të klientëve:
        - **R (Recency)** – Sa kohë ka blerë për herë të fundit? (më i ri = më i mirë)
        - **F (Frequency)** – Sa herë ka blerë? (më shumë = më i mirë)
        - **M (Monetary)** – Sa ka shpenzuar? (më shumë = më i mirë)

        Çdo klient merr një skor 1-3 për çdo dimension, pastaj grupohet:
        🟢 **Champions** · 🔵 **Loyal** · 🟡 **At Risk** · 🔴 **Lost**
        """)

    if df_raw is not None:
        df_rfm_base = df_raw.copy()
        if agj_sel != "Të gjithë": df_rfm_base = df_rfm_base[df_rfm_base["ForcaShitese"] == agj_sel]
        if grup_sel != "Të gjitha": df_rfm_base = df_rfm_base[df_rfm_base["Grup_Filtri"] == grup_sel]

        sot = datetime.now()
        rfm = (df_rfm_base.groupby("Klienti").agg(
            Recency=("Data", lambda x: (sot - x.max()).days),
            Frequency=("Data", "count"),
            Monetary=("Vlera_Historike", "sum"),
            KG_Total=("kg", "sum"),
        ).reset_index())

        # Skorimi (1=i keq, 3=i mirë; për R është e kundërt)
        rfm["R_Score"] = pd.qcut(rfm["Recency"], q=3, labels=[3, 2, 1]).astype(int)
        rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=3, labels=[1, 2, 3]).astype(int)
        rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), q=3, labels=[1, 2, 3]).astype(int)
        rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]

        def segmento(row):
            s = row["RFM_Score"]
            r = row["R_Score"]
            if s >= 8: return "🟢 Champions"
            elif s >= 6: return "🔵 Loyal"
            elif s >= 4 and r >= 2: return "🟡 At Risk"
            else: return "🔴 Lost / Churned"

        rfm["Segmenti"] = rfm.apply(segmento, axis=1)

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total Klientë", len(rfm))
        c2.metric("🟢 Champions", len(rfm[rfm["Segmenti"] == "🟢 Champions"]))
        c3.metric("🟡 At Risk", len(rfm[rfm["Segmenti"] == "🟡 At Risk"]))
        c4.metric("🔴 Lost", len(rfm[rfm["Segmenti"] == "🔴 Lost / Churned"]))

        st.divider()

        col_l, col_r = st.columns([2, 1])
        with col_l:
            st.subheader("📋 Lista e Klientëve me Segmentin")
            rfm_display = rfm[["Klienti", "Segmenti", "Recency", "Frequency", "Monetary", "KG_Total", "RFM_Score"]].copy()
            rfm_display = rfm_display.sort_values("RFM_Score", ascending=False)
            st.dataframe(
                rfm_display,
                column_config={
                    "Klienti": "Klienti",
                    "Segmenti": "Segmenti",
                    "Recency": st.column_config.NumberColumn("Ditë nga blerja e fundit", format="%d"),
                    "Frequency": st.column_config.NumberColumn("Nr. Faturave", format="%d"),
                    "Monetary": st.column_config.NumberColumn("Vlera Totale (L)", format="%d"),
                    "KG_Total": st.column_config.NumberColumn("KG Totale", format="%d"),
                    "RFM_Score": st.column_config.NumberColumn("Skor RFM", format="%d"),
                },
                hide_index=True, use_container_width=True, height=450,
            )

        with col_r:
            st.subheader("🗂️ Shpërndarja")
            seg_counts = rfm["Segmenti"].value_counts().reset_index()
            seg_counts.columns = ["Segmenti", "Nr_Klienteve"]
            colors = {"🟢 Champions": "#10b981", "🔵 Loyal": "#3b82f6",
                      "🟡 At Risk": "#f59e0b", "🔴 Lost / Churned": "#ef4444"}
            fig_seg = px.pie(seg_counts, values="Nr_Klienteve", names="Segmenti",
                             color="Segmenti", color_discrete_map=colors, hole=0.4)
            fig_seg.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0),
                                  legend=dict(orientation="v"))
            st.plotly_chart(fig_seg, use_container_width=True)

            st.subheader("💰 Vlera sipas Segmentit")
            seg_val = rfm.groupby("Segmenti")["Monetary"].sum().reset_index()
            for _, r in seg_val.iterrows():
                pct = r["Monetary"] / rfm["Monetary"].sum() * 100
                color = colors.get(r["Segmenti"], "#64748b")
                st.markdown(f"""
                <div style="margin:6px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:3px;">
                        <span>{r['Segmenti']}</span><span style="font-weight:600">{pct:.1f}%</span>
                    </div>
                    <div style="background:#f1f5f9;border-radius:4px;height:8px;">
                        <div style="background:{color};width:{pct:.1f}%;height:8px;border-radius:4px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Rekomandime
        st.subheader("💡 Rekomandime strategjike")
        cols_rec = st.columns(4)
        rekomandime = [
            ("🟢 Champions", "#10b981", "Shpërblejini! Ofrojuni produkte ekskluzive dhe bëni brand ambassadors."),
            ("🔵 Loyal", "#3b82f6", "Ofroni loyalty program. Inkurajojini të provojnë produkte të reja."),
            ("🟡 At Risk", "#f59e0b", "Kontakto menjëherë! Ofro zbritje ose ofertë speciale për rikuperim."),
            ("🔴 Lost / Churned", "#ef4444", "Analizoni arsyen e humbjes. Kampanjë rikuperimi me ofertë agresive."),
        ]
        for col, (seg, color, rec) in zip(cols_rec, rekomandime):
            n = len(rfm[rfm["Segmenti"] == seg])
            with col:
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:16px;border-top:4px solid {color};
                            box-shadow:0 2px 6px rgba(0,0,0,0.08);height:100%;">
                    <div style="font-weight:700;margin-bottom:6px;">{seg}</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{color};margin-bottom:8px;">{n} klientë</div>
                    <div style="font-size:0.82rem;color:#64748b;line-height:1.5;">{rec}</div>
                </div>
                """, unsafe_allow_html=True)

        csv_rfm = rfm_display.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Shkarko RFM CSV", csv_rfm, "analiza_rfm.csv", "text/csv")


# =========================================================
# MODULI: ASISTENTI AI
# =========================================================
elif page == "🤖 Asistenti AI":
    st.title("Strategjia e Shitjeve & Agjenda Inteligjente")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if agj_sel == "Të gjithë":
        st.warning("⚠️ Zgjidhni një agjent specifik në sidebar.")
    else:
        sot = datetime.now()
        data_sot_str = sot.strftime("%d/%m/%Y")
        df_tmp = df_raw.copy()
        df_tmp.columns = [c.lower() for c in df_tmp.columns]

        mask_ref = (df_tmp["data"].dt.date >= start_date) & (df_tmp["data"].dt.date <= end_date)
        df_agj_ref = df_tmp[mask_ref & (df_tmp["forcashitese"] == agj_sel)]
        n_months_ref = max(1, (end_date.year - start_date.year) * 12 +
                           (end_date.month - start_date.month))

        kl_target = df_agj_ref.groupby("klienti")["kg"].sum().reset_index()
        kl_target["Target_Muaj"] = (kl_target["kg"] / n_months_ref) * (1 + rritja / 100)

        mask_live = ((df_tmp["data"].dt.year == sot.year) &
                     (df_tmp["data"].dt.month == sot.month))
        df_live_agj = df_tmp[mask_live & (df_tmp["forcashitese"] == agj_sel)]
        kl_real_det = df_live_agj.groupby(["klienti", "data"]).agg({"kg": "sum"}).reset_index()
        statusi_real = kl_real_det.groupby("klienti")["kg"].sum().reset_index()

        full_map = pd.merge(kl_target, statusi_real, on="klienti", how="left").fillna(0)
        full_map["Ecuria"] = full_map["kg_y"] / full_map["Target_Muaj"] * 100
        full_map["Mbetja_KG"] = (full_map["Target_Muaj"] - full_map["kg_y"]).clip(lower=0)

        total_kliente = df_tmp[df_tmp["forcashitese"] == agj_sel]["klienti"].nunique()
        vizitat = kl_real_det.groupby("klienti")["data"].nunique().reset_index()
        double_visits = vizitat[vizitat["data"] > 1]["klienti"].tolist()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Total Klientë", total_kliente)
        c2.metric("✅ Vizituar (Muaj)", len(statusi_real))
        c3.metric("⏳ Pa vizituar", total_kliente - len(statusi_real))
        c4.metric("🔁 Double Visits", len(double_visits),
                  help="Klientë të faturuar >1 herë këtë muaj.")

        st.info("💡 **Mbetja KG** = (Targeti i Planifikimit) - (Shitjet reale muajit korrent).")

        def mark_sot(x):
            d = x.strftime("%d/%m/%Y")
            return f"⭐ {d} (SOT)" if d == data_sot_str else d

        tab1, tab2, tab3 = st.tabs(["🔴 Kritikë (60+ ditë)", "🟡 Prapa Planit", "🔵 Pa vizitë këtë muaj"])

        with tab1:
            kufiri_h = sot - pd.Timedelta(days=60)
            bf = (df_tmp[df_tmp["forcashitese"] == agj_sel]
                  .groupby("klienti")["data"].max().reset_index())
            kl_h = bf[bf["data"] < kufiri_h].copy()
            kl_h["Blerja e Fundit"] = kl_h["data"].apply(mark_sot)
            kl_h["Vizito"] = False
            kl_h["Pezull"] = False
            ed_h = st.data_editor(kl_h[["Vizito", "Pezull", "klienti", "Blerja e Fundit"]],
                                  key="humb_v4", hide_index=True, use_container_width=True)

        with tab2:
            rrz = (full_map[(full_map["Ecuria"] < 50) & (full_map["kg_y"] > 0)]
                   .sort_values("Target_Muaj", ascending=False).copy())
            rrz["Vizito"] = False; rrz["Pezull"] = False
            ed_r = st.data_editor(rrz[["Vizito", "Pezull", "klienti", "Target_Muaj", "Ecuria"]],
                column_config={"Ecuria": st.column_config.NumberColumn(format="%.1f%%")},
                key="rrez_v4", hide_index=True, use_container_width=True)

        with tab3:
            jov = (full_map[full_map["kg_y"] == 0]
                   .sort_values("Target_Muaj", ascending=False).copy())
            jov["Vizito"] = False; jov["Pezull"] = False
            ed_s = st.data_editor(jov[["Vizito", "Pezull", "klienti", "Target_Muaj"]],
                column_config={
                    "Vizito": st.column_config.CheckboxColumn("Zgjidh"),
                    "Pezull": st.column_config.CheckboxColumn("Pezull"),
                    "Target_Muaj": st.column_config.NumberColumn("Objektivi KG"),
                },
                key="sugj_v4", hide_index=True, use_container_width=True)

        # Procesimi i selektimeve (i rregulluar - pa duplikim)
        s_h = ed_h[(ed_h["Vizito"] == True) & (ed_h["Pezull"] == False)]["klienti"].tolist()
        s_r = ed_r[(ed_r["Vizito"] == True) & (ed_r["Pezull"] == False)]["klienti"].tolist()
        s_s = ed_s[(ed_s["Vizito"] == True) & (ed_s["Pezull"] == False)]["klienti"].tolist()
        lista_finale = list(set(s_h + s_r + s_s))

        st.divider()
        if lista_finale:
            st.success(f"✅ Agjenda u krijua me **{len(lista_finale)}** klientë.")
            c_r1, c_r2 = st.columns(2)

            if c_r1.button("📊 Raporti i Klientëve (KG & Vlera)"):
                cmimi_ref = 125
                rep_kl = full_map[full_map["klienti"].isin(lista_finale)].copy()
                rep_kl["Vlera"] = rep_kl["Mbetja_KG"] * cmimi_ref
                st.dataframe(rep_kl[["klienti", "Mbetja_KG", "Vlera"]], use_container_width=True)
                t_kg = rep_kl["Mbetja_KG"].sum()
                t_vl = rep_kl["Vlera"].sum()
                st.markdown(f"**TOTALI: {t_kg:,.1f} KG | {t_vl:,.1f} Lekë**")

            if c_r2.button("📦 Raporti i Artikujve për Ngarkesë"):
                art_data = []
                for k in lista_finale:
                    mbetja = full_map[full_map["klienti"] == k]["Mbetja_KG"].values[0]
                    kufiri_g = sot - pd.Timedelta(days=90)
                    hist = df_tmp[(df_tmp["klienti"] == k) & (df_tmp["data"] < kufiri_g)]
                    akt = df_tmp[(df_tmp["klienti"] == k) & (df_tmp["data"] >= kufiri_g)]
                    mungesa = [a for a in hist["artikulli"].unique() if a not in akt["artikulli"].unique()]
                    if mungesa:
                        spp = mbetja / len(mungesa[:3])
                        for m in mungesa[:3]:
                            art_data.append({"Artikulli": m, "Sasia KG": spp})
                    else:
                        art_data.append({"Artikulli": "PORTOFOL DIVERS", "Sasia KG": mbetja})
                if art_data:
                    df_af = pd.DataFrame(art_data)
                    rap = df_af.groupby("Artikulli")["Sasia KG"].sum().reset_index()
                    st.dataframe(rap.sort_values("Sasia KG", ascending=False), use_container_width=True)
                    st.markdown(f"**TOTALI: {rap['Sasia KG'].sum():,.1f} KG**")
        else:
            st.info("Zgjidhni klientët në tab-et e mësipërme.")


# =========================================================
# MODULI: ROUTE PLAN AI
# =========================================================
elif page == "🗺️ Route Plan AI":
    st.title("Route Plan AI · Strategjia Ditore")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if agj_sel == "Të gjithë":
        st.warning("⚠️ Ju lutem zgjidhni një agjent specifik.")
    else:
        df_tmp = df_raw.copy()
        df_tmp.columns = [c.lower() for c in df_tmp.columns]

        mask_ref = (df_tmp["data"].dt.date >= start_date) & (df_tmp["data"].dt.date <= end_date)
        df_agj = df_tmp[mask_ref & (df_tmp["forcashitese"] == agj_sel)]
        n_months_ref = max(1, (end_date.year - start_date.year) * 12 +
                           (end_date.month - start_date.month))
        kl_target = df_agj.groupby("klienti")["kg"].sum().reset_index()
        kl_target["Target_Muaj"] = (kl_target["kg"] / n_months_ref) * (1 + rritja / 100)

        kufiri_h = datetime.now() - pd.Timedelta(days=60)
        bf = (df_tmp[df_tmp["forcashitese"] == agj_sel].groupby("klienti")["data"].max().reset_index())
        kl_kritike = bf[bf["data"] < kufiri_h]["klienti"].tolist()

        kl_target["kategoria"] = "Stabilë"
        kl_target.loc[kl_target["klienti"].isin(kl_kritike), "kategoria"] = "Kritikë"
        limit_r = kl_target["Target_Muaj"].median()
        kl_target.loc[(kl_target["Target_Muaj"] > limit_r) &
                      (kl_target["kategoria"] != "Kritikë"), "kategoria"] = "Në Rrezik"

        klientet_total = kl_target.sort_values(["kategoria", "Target_Muaj"], ascending=[True, False])
        n_kl = len(klientet_total)
        kpd = max(1, n_kl // 26)

        st.subheader(f"📊 {n_kl} klientë · ~{kpd} klientë/ditë")

        dita = st.slider("Zgjidh ditën e punës (1-26):", 1, 26, 1)
        s_idx = (dita - 1) * kpd
        e_idx = n_kl if dita == 26 else s_idx + kpd
        kl_dites = klientet_total.iloc[s_idx:e_idx]

        # Statistika e ditës
        n_kritike = len(kl_dites[kl_dites["kategoria"] == "Kritikë"])
        n_rrezik = len(kl_dites[kl_dites["kategoria"] == "Në Rrezik"])
        n_stabil = len(kl_dites[kl_dites["kategoria"] == "Stabilë"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📍 Klientë sot", len(kl_dites))
        c2.metric("🔴 Kritikë", n_kritike)
        c3.metric("🟡 Në Rrezik", n_rrezik)
        c4.metric("🟢 Stabilë", n_stabil)

        st.info(f"📍 Plani për Ditën e Punës **#{dita}**")

        for _, row in kl_dites.iterrows():
            kl = row["klienti"]
            kat = row["kategoria"]
            target = row["Target_Muaj"]
            icon = "🔴" if kat == "Kritikë" else "🟡" if kat == "Në Rrezik" else "🟢"

            with st.expander(f"{icon} {kl} · {kat} · Target: {target:,.1f} KG"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**Objektivi:** {target:,.1f} KG")
                    kufiri_g = datetime.now() - pd.Timedelta(days=90)
                    hist = df_tmp[(df_tmp["klienti"] == kl) & (df_tmp["data"] < kufiri_g)]
                    akt = df_tmp[(df_tmp["klienti"] == kl) & (df_tmp["data"] >= kufiri_g)]
                    mungojne = [a for a in hist["artikulli"].unique() if a not in akt["artikulli"].unique()]
                    if mungojne:
                        st.write("🛒 **Artikujt Prioritarë:**")
                        for art in mungojne[:3]:
                            st.write(f"  - {art}")
                    else:
                        st.write("🛒 Fokus te rritja e volumit të artikujve bazë.")
                with c2:
                    if kat == "Kritikë":
                        st.error("⚠️ Rikuperim urgjent!")
                    elif kat == "Në Rrezik":
                        st.warning("🛡️ Mbroje planin!")
                    else:
                        st.success("📈 Rrit volumin!")

        st.divider()
        if st.button("📥 Shkarko Planin 26-Ditor (CSV)"):
            export_df = klientet_total.copy()
            export_df["Dita e Punes"] = [(i // kpd) + 1 for i in range(len(export_df))]
            export_df.loc[export_df["Dita e Punes"] > 26, "Dita e Punes"] = 26
            csv = export_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Kliko këtu", csv, f"Route_Plan_{agj_sel}.csv", "text/csv")


# =========================================================
# MODULI: EKSPORT EXCEL (I RI)
# =========================================================
elif page == "📥 Eksport Excel":
    st.title("Eksport Excel · Të gjitha Modulet")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}** · Grupi: **{grup_sel}**")

    st.markdown("""
    <div class="info-banner">
    📌 Ky modul eksporton të dhënat e filtruara nga të gjitha modulet në një skedar Excel me sheet-e të ndara.
    </div>
    """, unsafe_allow_html=True)

    if df_raw is not None:
        sot = datetime.now()
        dff = filtro_df(df_raw)
        df_live = df_raw[(df_raw["Data"].dt.year == sot.year) &
                         (df_raw["Data"].dt.month == sot.month)].copy()
        if grup_sel != "Të gjitha": df_live = df_live[df_live["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë": df_live = df_live[df_live["ForcaShitese"] == agj_sel]

        n_months = max(1, (end_date.year - start_date.year) * 12 +
                       (end_date.month - start_date.month))

        # Sheet 1: Realizimi
        gp_target = dff.groupby("kat").agg({"kg": "sum"}).reset_index()
        gp_target["KG_Target"] = (gp_target["kg"] / n_months) * (1 + rritja / 100)
        gp_live = df_live.groupby("kat").agg({"kg": "sum"}).reset_index().rename(columns={"kg": "KG_Real"})
        df_real = pd.merge(gp_target[["kat", "KG_Target"]], gp_live, on="kat", how="left").fillna(0)
        df_real["Ecuria_%"] = (df_real["KG_Real"] / df_real["KG_Target"] * 100).round(1)

        # Sheet 2: Planifikimi
        gp_plan = (dff.groupby(["ForcaShitese", "Klienti", "kat", "Artikulli"])
                   .agg({"kg": "sum", "Vlera_Historike": "sum"}).reset_index())
        gp_plan["Plani_KG"] = (gp_plan["kg"] / n_months) * (1 + rritja / 100)
        gp_plan["Vlera_Planifikuar"] = gp_plan["Plani_KG"] * (gp_plan["Vlera_Historike"] / gp_plan["kg"].replace(0, 1))

        # Sheet 3: Gap Analysis
        df_m = df_raw[df_raw["statusi"].astype(str).str.upper() == "AKTIV"].copy()
        if agj_sel != "Të gjithë": df_m = df_m[df_m["ForcaShitese"] == agj_sel]
        if grup_sel != "Të gjitha": df_m = df_m[df_m["Grup_Filtri"] == grup_sel]
        kufiri = sot - pd.Timedelta(days=90)
        sh_h = df_m[df_m["Data"] < kufiri]
        sh_a = df_m[df_m["Data"] >= kufiri]
        ph = sh_h.groupby(["Klienti", "Artikulli"]).agg({"Data": "max", "kg": "sum"}).reset_index()
        pa = sh_a[["Klienti", "Artikulli"]].drop_duplicates()
        pa["Blerë"] = True
        gaps = pd.merge(ph, pa, on=["Klienti", "Artikulli"], how="left")
        gaps = gaps[gaps["Blerë"].isna()][["Klienti", "Artikulli", "Data", "kg"]].copy()
        gaps["Data"] = gaps["Data"].dt.strftime("%d/%m/%Y")
        gaps.columns = ["Klienti", "Artikulli", "Blerja e Fundit", "KG Historike"]

        # Sheet 4: Historiku i plotë
        df_hist_exp = dff[["Data", "ForcaShitese", "Klienti", "Artikulli", "kat", "kg", "Vlera_Historike"]].copy()
        df_hist_exp["Data"] = df_hist_exp["Data"].dt.strftime("%d/%m/%Y")

        # Sheet 5: Shitjet muajit korrent
        df_live_exp = df_live[["Data", "ForcaShitese", "Klienti", "Artikulli", "kg", "Vlera_Historike"]].copy()
        df_live_exp["Data"] = df_live_exp["Data"].dt.strftime("%d/%m/%Y")

        sheets = {
            f"Realizimi_{muajt_sq.get(sot.month)}": df_real,
            "Planifikimi": gp_plan[["ForcaShitese", "Klienti", "kat", "Artikulli", "Plani_KG", "Vlera_Planifikuar"]],
            "Gap_Analysis_90d": gaps,
            f"Shitjet_{muajt_sq.get(sot.month)}": df_live_exp,
            "Historiku_Plote": df_hist_exp,
        }

        # Preview
        st.subheader("👁️ Preview sheet-eve")
        tab_names = list(sheets.keys())
        tabs = st.tabs(tab_names)
        for tab, (sh_name, sh_df) in zip(tabs, sheets.items()):
            with tab:
                st.caption(f"{len(sh_df):,} rreshta")
                st.dataframe(sh_df.head(50), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📥 Shkarko")
        agj_emri = agj_sel.replace(" ", "_") if agj_sel != "Të gjithë" else "Gjithe_Agjentet"
        emri_skedarit = f"DEKA_Raport_{agj_emri}_{sot.strftime('%d_%m_%Y')}.xlsx"

        if st.button("🔄 Gjenero skedarin Excel", use_container_width=True):
            with st.spinner("Duke krijuar Excel-in..."):
                excel_bytes = df_to_excel_bytes(sheets)
            st.download_button(
                label=f"📥 Shkarko: {emri_skedarit}",
                data=excel_bytes,
                file_name=emri_skedarit,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.success(f"✅ Excel u gjenerua me {len(sheets)} sheet-e!")
