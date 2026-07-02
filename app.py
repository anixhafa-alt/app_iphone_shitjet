import base64

import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os
import numpy as np
import time

# --- Moduli i unifikuar AI (v3.0) ---
from ai_modules_improved import render_plan_ditor
from analiza_module import render_analiza

# =========================================================
# region ==================================================
st.set_page_config(page_title="Sistemi i Planifikimit - DEKA SQL", layout="wide")

# Fjalori për Muajt Shqip
muajt_sq = {
    1: "Janar",
    2: "Shkurt",
    3: "Mars",
    4: "Prill",
    5: "Maj",
    6: "Qershor",
    7: "Korrik",
    8: "Gusht",
    9: "Shtator",
    10: "Tetor",
    11: "Nëntor",
    12: "Dhjetor",
}
# endregion


# =========================================================
# 2. SISTEMI I SIGURISE (LOGIN)
# region ==================================================
def password_entered():
    # Përdorim .get() në vend të ["password"] për të shmangur KeyError
    if st.session_state.get("password", "") == "a":
        st.session_state["password_correct"] = True
        del st.session_state["password"]  # fshijmë fjalëkalimin për siguri
    else:
        st.session_state["password_correct"] = False


def check_password():
    if "password_correct" not in st.session_state:
        st.markdown(
            "<h2 style='text-align: center;'>Hyrja në Sistem</h2>",
            unsafe_allow_html=True,
        )
        st.text_input(
            "Shkruaj fjalëkalimin:",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Fjalëkalim i gabuar!",
            type="password",
            on_change=password_entered,
            key="password",
        )
        return False
    else:
        return True


if not check_password():
    st.stop()
# endregion

# =========================================================
# 3. LOGO DHE CSS I VERSIONIT (STILI AXION)
# region ==================================================
EMRI_FOTOS = "logo.png"

if os.path.exists(EMRI_FOTOS):
    try:
        logo_axion = Image.open(EMRI_FOTOS)
        st.sidebar.image(logo_axion, use_container_width=True)
    except Exception as e:
        st.sidebar.error(f"⚠️ Gabim gjatë leximit të logos: {e}")
else:
    st.sidebar.title("AXION")
    st.sidebar.error(f"❌ Skedari '{EMRI_FOTOS}' nuk u gjet në server.")

# Injektimi i CSS për afërsi maksimale të versionit në Sidebar
st.sidebar.markdown(
    """
    <style>
    /* Heqim hapësirën e tepërt që krijon veshja e imazhit në Streamlit */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    
    /* Tërheqim tekstin e versionit fort lart */
    .version-text {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 12px !important;
        color: #566573 !important;
        text-align: right;
        margin-top: -110px !important;
        margin-bottom: 20px !important;
        letter-spacing: 1px;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Shfaqja e versionit fiks nën logo
st.sidebar.markdown('<p class="version-text">v.1.1.0</p>', unsafe_allow_html=True)
# endregion


# =========================================================
# 4. NAVIGIMI (PANEL KONTROLLI) - ME EMËRTIMET E SAKTA
# region ==================================================
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1.5"></rect>
            <rect x="14" y="3" width="7" height="7" rx="1.5"></rect>
            <rect x="14" y="14" width="7" height="7" rx="1.5"></rect>
            <rect x="3" y="14" width="7" height="7" rx="1.5"></rect>
        </svg>
        <h1 style="font-size: 1.75rem; font-weight: 700; margin: 0; padding: 0; color: #31333F;">
            Panel Konrolli
        </h1>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Zgjidh Modulin:",
    [
        "Shitjet Ditore",
        "Realizimi",
        "Planifikimi",
        "🎯 Plani Ditor",  # Moduli i ri i unifikuar — zëvendëson 4 modulet AI
        "🎯 Plani sipas Strukturës B",
        "Mundësitë",
        "Historiku",
        "AI Assistant",
        "Analiza nga 2020",  # Dashboard interaktiv (trendet, top kategorite, agjentet)
    ],
)
# endregion


# =========================================================
# 5. NGARKIMI DHE BASHKIMI I TE DHENAVE (SQL + EXCEL)
# region ==================================================
@st.cache_data(ttl=600)
def load_all_data():
    try:
        conn = st.connection("sql", type="sql")
        df_sql = conn.query(
            "SELECT Data, ForcaShitese, KodiKlient, Klienti, Qyteti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView"
        )
        df_sql.columns = df_sql.columns.str.strip()
        df_sql["Data"] = pd.to_datetime(df_sql["Data"], errors="coerce")

        df_map = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
        df_map.columns = df_map.columns.str.strip()
        df_map = df_map[["KODI", "KATEG.", "KG/SKU", "NGA LISTA E CMIMEVE"]].copy()
        df_map["KODI"] = df_map["KODI"].astype(str).str.strip()

        df = pd.merge(df_sql, df_map, left_on="KodiArt", right_on="KODI", how="left")

        df["kg"] = df["Sasia"] * df["KG/SKU"].fillna(0)
        df.rename(
            columns={"KATEG.": "kat", "NGA LISTA E CMIMEVE": "statusi"}, inplace=True
        )
        df["Vlera_Historike"] = pd.to_numeric(
            df["VleraRresht"], errors="coerce"
        ).fillna(0)
        df["kat"] = df["kat"].fillna("ETJ")
        df["statusi"] = df["statusi"].fillna("inaktiv")

        def klasifiko_kategorine(k):
            val = str(k).upper()
            if val == "V" or "OLIM" in val:
                return "OLIM"
            elif val == "ETJ":
                return "ETJ"
            else:
                return "DEKA"

        df["Grup_Filtri"] = df["kat"].apply(klasifiko_kategorine)
        return df
    except Exception as e:
        st.error(f"Gabim teknik te load_all_data: {e}")
        return None


@st.cache_data(ttl=600)
def load_customer_list():
    try:
        conn = st.connection("sql", type="sql")
        query = """
            SELECT 
                [Kodi] AS KodiKlient, 
                [Emri] AS Klienti, 
                [Zona] AS ForcaShiteseAktuale, 
                [Qyteti] AS Rajoni
            FROM dbo.KlientetListView
        """
        df_klientet = conn.query(query)
        df_klientet.columns = df_klientet.columns.str.strip()

        if "KodiKlient" in df_klientet.columns:
            df_klientet["KodiKlient"] = (
                df_klientet["KodiKlient"].astype(str).str.strip()
            )

        koordinatat_qyteteve = {
            "TIRANE": (41.3275, 19.8187),
            "DURRES": (41.3242, 19.4564),
            "ELBASAN": (41.1125, 20.0822),
            "VLORE": (40.4661, 19.4897),
            "SHKODER": (42.0683, 19.5126),
            "FIER": (40.7275, 19.5622),
            "KORCE": (40.6158, 20.7778),
            "BERAT": (40.7058, 19.9522),
            "LUSHNJE": (40.9419, 19.7028),
        }

        def ploteso_koordinatat(row):
            qyteti_pastruar = str(row["Rajoni"]).upper().strip()
            qendrat = koordinatat_qyteteve.get(qyteti_pastruar, (41.3275, 19.8187))
            return pd.Series(
                [
                    qendrat[0] + np.random.uniform(-0.03, 0.03),
                    qendrat[1] + np.random.uniform(-0.03, 0.03),
                ]
            )

        df_klientet[["Latitude", "Longitude"]] = df_klientet.apply(
            ploteso_koordinatat, axis=1
        )
        df_klientet["StatusiAktiv"] = True

        return df_klientet
    except Exception as e:
        st.error(f"⚠️ Gabim teknik gjatë leximit të regjistrit të klientëve: {e}")
        return None


df_klientet_regjistri = load_customer_list()
df_raw = load_all_data()

try:
    df_link = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
    df_link.columns = df_link.columns.str.strip()
    df_link = df_link[["KODI", "KATEG."]].rename(
        columns={"KODI": "KodiArt", "KATEG.": "KOD KAT"}
    )
except Exception as e:
    st.error(f"Gabim te sheet-i 'produktet': {e}")
    df_link = None

try:
    df_names = pd.read_excel("produkte+.xlsx", sheet_name="kat_prod")
    df_names.columns = df_names.columns.str.strip()
    df_names = df_names[["KOD KAT", "EMRI KAT"]]
except Exception as e:
    st.error(f"Gabim te sheet-i 'kat_prod': {e}")
    df_names = None

if df_raw is not None and df_link is not None:
    df_link["KodiArt"] = df_link["KodiArt"].astype(str).str.strip()
    df_raw["KodiArt"] = df_raw["KodiArt"].astype(str).str.strip()

    df_raw = pd.merge(df_raw, df_link, on="KodiArt", how="left")

    if df_names is not None:
        df_raw = pd.merge(df_raw, df_names, on="KOD KAT", how="left")
        df_raw["kat"] = (
            df_raw["EMRI KAT"].fillna(df_raw["KOD KAT"]).fillna("Pa Kategori")
        )
# endregion


# =========================================================
# RIFRESKIMI AUTOMATIK ÇDO 30 MINUTA (PA NGADALËSIM)
# region ==================================================
if "koha_rifreskimit_fundit" not in st.session_state:
    st.session_state["koha_rifreskimit_fundit"] = time.time()

if time.time() - st.session_state["koha_rifreskimit_fundit"] > 1800:
    st.cache_data.clear()
    st.session_state["koha_rifreskimit_fundit"] = time.time()
    st.rerun()
# endregion

# =========================================================
# 6. KORNIZA E RE E SINKRONIZIMIT
# region ==================================================
if df_raw is not None and not df_raw.empty:
    kolona_date = [c for c in df_raw.columns if c.lower() == "data"]
    if kolona_date:
        emer_kolone = kolona_date[0]
        datet_konvertuara = pd.to_datetime(df_raw[emer_kolone], errors="coerce")
        data_maksimale = datet_konvertuara.max()
        sot_data = datetime.now().date()

        with st.sidebar.container(border=True):
            if st.button("🔄 Rifresko nga SQL Server", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

            if pd.notnull(data_maksimale):
                koha_formatuar = data_maksimale.strftime("%d/%m/%Y - %H:%M:%S")
                if data_maksimale.date() == sot_data:
                    st.markdown(
                        f"🟢 Lidhja SQL: LIVE | <small style='color: #2e7d32;'>Fat. fundit: {koha_formatuar}</small>",
                        unsafe_allow_html=True,
                    )
                else:
                    vonesa = (sot_data - data_maksimale.date()).days
                    st.markdown(
                        f"🟡 Lidhja SQL: OK | <small style='color: #b78103;'>Fat. fundit: {koha_formatuar} ({vonesa} d. vonesë)</small>",
                        unsafe_allow_html=True,
                    )
    else:
        st.sidebar.error("⚠️ Nuk u gjet kolona 'DATA' në tabelë.")
# endregion


# =========================================================
# 7. FUNKSIONI: LIBRARIA PERMANENTE
# region ==================================================
@st.cache_resource
def merr_librarine_permanente():
    return {"Zgjedhje Manuale (Pa Ruajtje)": None}


# endregion


# =========================================================
# 8. FUNKSIONI KRYESOR: NDËRTIMI I SIDEBAR
# region ==================================================
def nderto_sidebar():
    if df_raw is not None and not df_raw.empty:
        if "start_d" not in st.session_state:
            st.session_state["start_d"] = df_raw["Data"].min().date()
        if "end_d" not in st.session_state:
            st.session_state["end_d"] = df_raw["Data"].max().date()
        if "rritja_val" not in st.session_state:
            st.session_state["rritja_val"] = 10
    else:
        st.error(
            "⚠️ Nuk u morën dot të dhënat nga databaza. Kontrollo lidhjen dhe secrets.toml."
        )
        st.stop()

    libraria_p = merr_librarine_permanente()
    opsionet_lib = list(libraria_p.keys())

    if (
        "plan_per_te_ngarkuar" in st.session_state
        and st.session_state["plan_per_te_ngarkuar"] is not None
    ):
        emri_planit = st.session_state["plan_per_te_ngarkuar"]
        plani_ruajtur = libraria_p.get(emri_planit)

        if plani_ruajtur is not None:
            st.session_state["start_d"] = plani_ruajtur["start"]
            st.session_state["end_d"] = plani_ruajtur["end"]
            st.session_state["rritja_val"] = plani_ruajtur["rritja"]
            st.session_state["date_input_key"] = (
                plani_ruajtur["start"],
                plani_ruajtur["end"],
            )
            st.session_state["rritja_input"] = plani_ruajtur["rritja"]

        st.session_state["plan_per_te_ngarkuar"] = None

    # MODULI: VENDOSJA E PLANIT SI EXPANDER (Tani ngjitet direkt poshtë kornizës së mësipërme)
    with st.sidebar.expander("Vendosja e Planit ⚙️", expanded=True):
        st.subheader("📂 Libraria e Planeve")

        def on_change_libraria():
            zgjedhja = st.session_state["temp_selectbox_key"]
            if zgjedhja != "Zgjedhje Manuale (Pa Ruajtje)":
                st.session_state["plan_per_te_ngarkuar"] = zgjedhja

        st.selectbox(
            "Thirr një plan të ruajtur:",
            options=opsionet_lib,
            index=0,
            key="temp_selectbox_key",
            on_change=on_change_libraria,
        )

        date_range = st.date_input(
            "Periudha referente:",
            value=(st.session_state["start_d"], st.session_state["end_d"]),
            key="date_input_key",
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state["start_d"], st.session_state["end_d"] = date_range

        rritja = st.number_input(
            "Rritja e planit (%)",
            value=st.session_state["rritja_val"],
            key="rritja_input",
        )
        st.session_state["rritja_val"] = rritja

        with st.expander("💾 Menaxho Librarinë (Ruaj / Fshi)"):
            st.markdown("**Shto Plan të Ri**")
            emri_planit_ri = st.text_input(
                "Emri i planit (psh: Maj 2026 - R1):", key="emri_ri_txt"
            )

            if st.button("➕ Ruaj Planin", use_container_width=True):
                if emri_planit_ri.strip() != "":
                    libraria_p[emri_planit_ri] = {
                        "start": st.session_state["start_d"],
                        "end": st.session_state["end_d"],
                        "rritja": st.session_state["rritja_val"],
                    }
                    st.success(f"✅ '{emri_planit_ri}' u ruajt!")
                    st.rerun()
                else:
                    st.error("Ju lutem vendosni një emër për planin.")

            st.divider()

            st.markdown("**Fshi një Plan ekzistues**")
            plane_per_fshirje = [
                p for p in opsionet_lib if p != "Zgjedhje Manuale (Pa Ruajtje)"
            ]

            if plane_per_fshirje:
                plani_fshirjes = st.selectbox(
                    "Zgjidh cilin dëshiron të fshish:",
                    options=plane_per_fshirje,
                    key="fshirje_sel_key",
                )
                if st.button("❌ Fshi Planin e Zgjedhur", use_container_width=True):
                    del libraria_p[plani_fshirjes]
                    st.warning(f"🗑️ '{plani_fshirjes}' u fshi!")
                    st.rerun()
            else:
                st.caption("Nuk ka plane të ruajtura për të fshirë.")

    # FILTRAT E TJERË
    grup_sel = st.sidebar.selectbox(
        "Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"]
    )

    agj_list = sorted(
        [str(x) for x in df_raw["ForcaShitese"].unique() if x not in ["nan", "None"]]
    )
    agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)

    k_list = (
        df_raw[df_raw["ForcaShitese"] == agj_sel]["Klienti"].unique()
        if agj_sel != "Të gjithë"
        else df_raw["Klienti"].unique()
    )
    klientet_selected = st.sidebar.multiselect("Zgjidh Klientin:", sorted(list(k_list)))

    start_date = st.session_state["start_d"]
    end_date = st.session_state["end_d"]

    st.sidebar.divider()
    if st.sidebar.button("Log Out"):
        st.session_state["password_correct"] = False
        st.rerun()

    with st.sidebar.expander("ℹ️ Detajet e përzgjedhjes", expanded=True):
        nr_aktiv = df_raw[df_raw["statusi"].astype(str).str.upper() == "AKTIV"][
            "Artikulli"
        ].nunique()
        nr_inaktiv = df_raw[df_raw["statusi"].astype(str).str.upper() != "AKTIV"][
            "Artikulli"
        ].nunique()

        st.write(
            f"**Periudha:** {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
        )
        st.write(f"📈 **Rritja e aplikuar:** {rritja}%")
        st.write(f"👤 **Agjenti:** {agj_sel}")
        st.write(
            f"🏢 **Klientë të zgjedhur:** {len(klientet_selected) if klientet_selected else 'Të gjithë'}"
        )
        st.write(f"📦 **Artikuj Aktivë:** {nr_aktiv}")
        st.write(f"🛑 **Artikuj Inaktivë:** {nr_inaktiv}")

    return start_date, end_date, rritja, grup_sel, agj_sel, klientet_selected


# endregion

# =========================================================
# 9. THIRRJA E FUNKSIONIT TË SIDEBAR
# region ==================================================
start_date, end_date, rritja, grup_sel, agj_sel, klientet_selected = nderto_sidebar()
# endregion

# =========================================================
# 10. MODULET
# region ==================================================
# ---------------------------------------------------------
# MODULI I RI I UNIFIKUAR: PLANI DITOR (v3.0)
# ---------------------------------------------------------
if page == "🎯 Plani Ditor":
    render_plan_ditor(
        df_raw,
        df_klientet_regjistri,
        agj_sel,
        start_date,
        end_date,
        rritja,
        grup_sel=grup_sel,
        klientet_selected=klientet_selected,
    )

# ---------------------------------------------------------
# MODULI: ANALIZA (Dashboard) databaza xlsb/paquet nga 2020
# ---------------------------------------------------------
elif page == "Analiza nga 2020":
    render_analiza()

# ---------------------------------------------------------
# MODULI: HISTORIKU
# ---------------------------------------------------------
elif page == "Historiku":
    # st.title("📚 Historiku i Shitjeve & Analiza e Artikujve")
    st.title("Historiku i Shitjeve & Analiza e Artikujve")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")
    if df_raw is not None:
        # 1. Krijojmë kopjen për punë
        df_hist = df_raw.copy()
        df_hist["Viti"] = df_hist["Data"].dt.year
        df_hist["Muaji"] = df_hist["Data"].dt.month

        # 2. APLIKIMI I FILTRAVE TË SIDEBAR-IT (Lidhja që mungonte)
        # Filtri i Agjentit
        if agj_sel != "Të gjithë":
            df_hist = df_hist[df_hist["ForcaShitese"] == agj_sel]

        # Filtri i Klientëve (nga Multiselect)
        if klientet_selected:
            df_hist = df_hist[df_hist["Klienti"].isin(klientet_selected)]

        # Filtri i Grupit (OLIM, DEKA, ETJ)
        if grup_sel != "Të gjitha":
            df_hist = df_hist[df_hist["Grup_Filtri"] == grup_sel]

        # 3. FILTRAT SPECIFIKË TË FAQES (Vitet dhe Kategoritë)
        st.subheader("🔍 Filtra shtesë për Historikun")
        c1, c2 = st.columns(2)
        with c1:
            vitet_e_disponueshme = sorted(df_hist["Viti"].unique(), reverse=True)
            viti_sel = st.multiselect(
                "Krahaso Vitet:", vitet_e_disponueshme, default=vitet_e_disponueshme[:2]
            )
        with c2:
            kat_list = sorted(df_hist["kat"].unique())
            kat_sel = st.multiselect("Filtro Kategoritë:", kat_list, default=kat_list)

        # Aplikojmë filtrat e faqes
        df_final = df_hist[
            df_hist["Viti"].isin(viti_sel) & df_hist["kat"].isin(kat_sel)
        ]

        # --- GRAFIKU I TRENDIT ---
        st.subheader("📈 Trendi Mujor (KG)")

        # Pasi df_final ka kaluar filtret e Agjentit, Klientëve dhe Grupit, bëjmë grupimin
        chart_data = df_final.groupby(["Viti", "Muaji"])["kg"].sum().reset_index()

        if not chart_data.empty:
            # Krijojmë pivot tabelën ku rreshtat janë muajt dhe kolonat janë vitet
            chart_pivot = chart_data.pivot(
                index="Muaji", columns="Viti", values="kg"
            ).fillna(0)

            # Renditim muajt si numra (1, 2, 3...) që të ruhet radha kronologjike
            chart_pivot = chart_pivot.sort_index()

            # Vendosim emrat e muajve me numër përpara (p.sh. "01. Janar") që Streamlit mos t'i prishë
            chart_pivot.index = [
                f"{m:02d}. {muajt_sq.get(m, m)}" for m in chart_pivot.index
            ]

            # Shfaqim grafikun e thjeshtë me vijat sipas viteve
            st.line_chart(chart_pivot)
        else:
            st.info("Nuk ka të dhëna për këtë përzgjedhje klientësh.")

        # --- TABELA E PLOTË E ARTIKUJVE (Kërkesa jote) ---
        st.divider()
        st.subheader("🏆 Lista e Plotë e Artikujve dhe Shpërndarja")

        # Grupimi i artikujve
        tabela_artikujt = (
            df_final.groupby(["Artikulli", "kat"])
            .agg(
                {
                    "kg": "sum",
                    "Vlera_Historike": "sum",
                    "Klienti": "nunique",  # Kjo gjen numrin e klientëve unikë
                }
            )
            .rename(
                columns={
                    "kg": "Totale KG",
                    "Vlera_Historike": "Vlera (L)",
                    "Klienti": "Nr. Klientëve",
                }
            )
            .sort_values("Totale KG", ascending=False)
        )

        # Shfaqja e listës së plotë me scroll
        st.dataframe(
            tabela_artikujt.style.format(
                {
                    "Totale KG": "{:,.1f}",
                    "Vlera (L)": "{:,.0f}",
                    "Nr. Klientëve": "{:,.0f}",
                }
            ),
            use_container_width="stretch",
            height=600,  # Lartësia që lejon të shohësh shumë rreshta
        )

        # Mundësia për shkarkim në Excel
        csv = tabela_artikujt.to_csv().encode("utf-8-sig")
        st.download_button(
            label="📥 Shkarko Listën e Plotë (CSV)",
            data=csv,
            file_name="historiku_artikujve.csv",
            mime="text/csv",
        )

# ---------------------------------------------------------
# MODULI: PLANIFIKIMI (ME EXPANDER-IN TE KOKA E FAQES)
# ---------------------------------------------------------
elif page == "Planifikimi" and df_raw is not None:

    sot = datetime.now()
    data_fundit_db = df_raw["Data"].max().strftime("%d/%m/%Y")

    # --- 📅 PËRZGJEDHJA E MUAJIT DHE VITIT PËR PLANIN ---
    st.sidebar.markdown("### 📅 Periudha e Planit")

    lista_muajve = [
        "Janar",
        "Shkurt",
        "Mars",
        "Prill",
        "Maj",
        "Qershor",
        "Korrik",
        "Gusht",
        "Shtator",
        "Tetor",
        "Nëntor",
        "Dhjetor",
    ]

    muaji_default_index = sot.month - 1
    muaji_i_zgjedhur = st.sidebar.selectbox(
        "Zgjidh Muajin:", lista_muajve, index=muaji_default_index
    )

    lista_viteve = list(range(sot.year - 1, sot.year + 4))
    viti_default_index = lista_viteve.index(sot.year) if sot.year in lista_viteve else 0
    viti_i_zgjedhur = st.sidebar.selectbox(
        "Zgjidh Vitin:", lista_viteve, index=viti_default_index
    )

    # --- 🛑 FILTRI: PËRJASHTIMI I KLIENTËVE PASIVË ---
    st.sidebar.markdown("### 💤 Filtri i Klientëve Pasivë")
    muajt_pasivitet = st.sidebar.number_input(
        "Përjashto klientët pa blerje në (muajt e fundit):",
        min_value=1,
        max_value=24,
        value=3,
        step=1,
    )

    # --- LOGJIKA E ÇMIMIT TË FUNDIT ---
    mask_past = (df_raw["Data"].dt.year < sot.year) | (
        (df_raw["Data"].dt.year == sot.year) & (df_raw["Data"].dt.month < sot.month)
    )
    df_past = df_raw[mask_past].copy()
    df_past["Cmimi_Rresht"] = df_past["Vlera_Historike"] / df_past["kg"].replace(0, 1)
    last_prices = df_past.sort_values("Data").drop_duplicates("KodiArt", keep="last")[
        ["KodiArt", "Cmimi_Rresht"]
    ]
    last_prices.rename(columns={"Cmimi_Rresht": "Cmimi_Fundit_Artikulli"}, inplace=True)

    # --- IDENTIFIKIMI I KLIENTËVE AKTIVË DHE PASIVË ---
    data_maksimale_db = df_raw["Data"].max()
    data_kufi_pasivitet = data_maksimale_db - pd.DateOffset(months=muajt_pasivitet)

    df_blerja_fundit = (
        df_raw.groupby(["Klienti", "ForcaShitese"])["Data"].max().reset_index()
    )
    df_blerja_fundit.rename(columns={"Data": "Data_Blerjes_Fundit"}, inplace=True)

    df_aktive_kohe = df_blerja_fundit[
        df_blerja_fundit["Data_Blerjes_Fundit"] >= data_kufi_pasivitet
    ]
    klientet_aktive_kohe = df_aktive_kohe["Klienti"].unique()

    df_pasive_baze = df_blerja_fundit[
        df_blerja_fundit["Data_Blerjes_Fundit"] < data_kufi_pasivitet
    ].copy()
    df_pasive_baze["Muaj_Pa_Blerje"] = (
        (data_maksimale_db - df_pasive_baze["Data_Blerjes_Fundit"]).dt.days / 30
    ).round(1)

    # --- FILTRIMI I PERIUDHËS HISTORIKE ---
    mask = (df_raw["Data"].dt.date >= start_date) & (df_raw["Data"].dt.date <= end_date)
    dff = df_raw.loc[mask].copy()
    dff = dff[dff["Klienti"].isin(klientet_aktive_kohe)]

    if grup_sel != "Të gjitha":
        dff = dff[dff["Grup_Filtri"] == grup_sel]

    # --- 🔍 KONTROLLI AUTOMATIK I EMRAVE TË KOLONAVE TË SQL ---
    kolona_kodi_agj_sql = next(
        (c for c in dff.columns if "KODI" in c.upper() and "FORCA" in c.upper()), None
    )
    if not kolona_kodi_agj_sql:
        kolona_kodi_agj_sql = next(
            (c for c in dff.columns if "KODI" in c.upper() and "AGJ" in c.upper()),
            "KodiForcashitese",
        )

    kolona_rajoni_sql = next(
        (
            c
            for c in dff.columns
            if "ZONA" in c.upper() or "RAJON" in c.upper() or "KODZONA" in c.upper()
        ),
        "KodZona",
    )

    if kolona_kodi_agj_sql not in dff.columns:
        dff[kolona_kodi_agj_sql] = "agj000"
    if kolona_rajoni_sql not in dff.columns:
        dff[kolona_rajoni_sql] = "Rajoni"

    dff["ForcaShitese"] = dff["ForcaShitese"].fillna("Pa Agjent")
    dff[kolona_kodi_agj_sql] = dff[kolona_kodi_agj_sql].fillna("agj000")
    dff[kolona_rajoni_sql] = dff[kolona_rajoni_sql].fillna("Rajoni")
    dff["kat"] = dff["kat"].fillna("ETJ")

    if agj_sel != "Të gjithë":
        dff = dff[dff["ForcaShitese"] == agj_sel]
        df_pasive_baze = df_pasive_baze[df_pasive_baze["ForcaShitese"] == agj_sel]

    if klientet_selected:
        dff = dff[dff["Klienti"].isin(klientet_selected)]

    n_months = max(
        1,
        (end_date.year - start_date.year) * 12
        + (end_date.month - start_date.month)
        + 1,
    )

    # --- AGREGIMI BAZË ---
    gp = (
        dff.groupby(
            [
                "ForcaShitese",
                kolona_kodi_agj_sql,
                kolona_rajoni_sql,
                "Klienti",
                "kat",
                "KodiArt",
                "Artikulli",
            ]
        )
        .agg({"kg": "sum", "Vlera_Historike": "sum"})
        .reset_index()
    )

    gp["Cmimi_Mes_Periudhes"] = gp["Vlera_Historike"] / gp["kg"].replace(0, 1)
    gp = gp.merge(last_prices, on="KodiArt", how="left")

    gp["Plani_KG"] = (gp["kg"] / n_months) * (1 + rritja / 100)
    gp["Vlera_Planifikuar"] = gp["Plani_KG"] * gp["Cmimi_Fundit_Artikulli"].fillna(
        gp["Cmimi_Mes_Periudhes"]
    )

    # --- RENDITJA ZYRTARE E NËN-KATEGORIVE ---
    nen_kat_renditja = [
        "MATIK1",
        "MATIK2",
        "DORE",
        "LIQUID1",
        "LIQUID2",
        "ZBARDHUES",
        "SOFT1",
        "SOFT2",
        "ENESH",
        "XHEL",
        "PLLAKA",
        "KREM",
        "SAPUN",
        "ANTIBAKTERIAL",
        "DEZINFEKTUES",
        "ETJ",
        "SET",
    ]

    def gjej_nen_kategorine_zyrtare(rresht):
        art_up = str(rresht["Artikulli"]).upper().replace(" ", "")
        kat_up = str(rresht["kat"]).upper().replace(" ", "")

        if "VAJ" in kat_up or "OLIM" in kat_up:
            return "VAJ"
        if "MATIK" in art_up:
            if "1" in art_up or "SUPER" in art_up:
                return "MATIK1"
            return "MATIK2"
        if "DORE" in art_up or "HAND" in art_up:
            return "DORE"
        if "LIQUID" in art_up or "LIKUID" in art_up:
            if "1" in art_up:
                return "LIQUID1"
            return "LIQUID2"
        if "ZBARDHUES" in art_up or "ACE" in art_up or "ZBERDH" in art_up:
            return "ZBARDHUES"
        if "SOFT" in art_up or "ZBUTES" in art_up:
            if "1" in art_up:
                return "SOFT1"
            return "SOFT2"
        if "ENESH" in art_up or "ENVE" in art_up or "DISH" in art_up:
            return "ENESH"
        if "XHEL" in art_up or "GEL" in art_up:
            return "XHEL"
        if "PLLAKA" in art_up or "SURE" in art_up:
            return "PLLAKA"
        if "KREM" in art_up or "CREAM" in art_up:
            return "KREM"
        if "SAPUN" in art_up or "SOAP" in art_up:
            return "SAPUN"
        if "ANTIBAKTERIAL" in art_up:
            return "ANTIBAKTERIAL"
        if "DEZINFEKT" in art_up:
            return "DEZINFEKTUES"
        if "SET" in art_up:
            return "SET"
        return "ETJ"

    gp["NenKatZyrtare"] = gp.apply(gjej_nen_kategorine_zyrtare, axis=1)

    # =========================================================
    # 👑 KOKA E FAQES (TITULLI, INFO-BAR DHE EXPANDER-I)
    # =========================================================
    st.title(f"Plani: {muaji_i_zgjedhur} {viti_i_zgjedhur}")
    st.markdown(f"### 👤 Agjenti Aktual: **{agj_sel}**")
    st.info(
        f"💾 Update i fundit në DB: **{data_fundit_db}** | Grupi i zgjedhur: **{grup_sel}**"
    )

    # --- ℹ️ BLLOKU INFORMATIV VENDOSET KËTU (TE KOKA) ---
    with st.expander("ℹ️ Si llogaritet ky plan? (Kliko për ta hapur)"):
        st.markdown(f"""
        Ky modul llogarit planin e shitjeve në sasi (KG) dhe vlerë (Lekë) bazuar në hapat e mëposhtëm:
        
        1. **Ri-alokimi te Agjenti Aktual:** Përpara çdo llogaritjeje, të dhënat historike të shitjeve të çdo klienti kryqëzohen me regjistrin `KlientetListView` nga SQL. Gjatë këtij procesi, pastrohen dublikimet e mundshme të klientëve për të parandaluar fryrjen artificiale të volumeve. Historiku i shitjeve zhvendoset automatikisht te **Agjenti Aktual** (kolona `Zona`), duke mundësuar që plani të grupohet sipas strukturës aktuale të terrenit.
        
        2. **Heqja e Klientëve Pasivë:** Sistemi analizon blerjen e fundit absolute të çdo klienti. Nëse blerja e tyre e fundit është më e vjetër se **{muajt_pasivitet} muaj** nga përditësimi i fundit i sistemit ({data_fundit_db}), ata konsiderohen pasivë dhe hiqen automatikisht nga plani.
        
        3. **Plani në KG:** Merret sasia totale në KG e periudhës së përzgjedhur historike, pjesëtohet për numrin e muajve të asaj periudhe (për to gjetur mesataren mujore) dhe rritet me përqindjen e përzgjedhur:
           $$\\text{{Plani KG}} = \\left( \\frac{{\\text{{KG Historike}}}}{{\\text{{Numri i Muajve}}}} \\right) \\times \\left(1 + \\frac{{\\text{{Përqindja e Rritjes}}}}{{100}}\\right)$$
        
        4. **Çmimi i Fundit:** Për çdo artikull merret çmimi i shitjes së fundit historike në të gjithë sistemin, duke përjashtuar muajin korrent.
        
        5. **Vlera e Planifikuar:** Shumëzohet **Plani KG** me **Çmimin e Fundit** të artikullit. Nëse artikulli nuk ka një çmim të fundit në historik, sistemi përdor si alternativë *Çmimin Mesatar i Periudhës* së përzgjedhur:
           $$\\text{{Vlera e Planifikuar}} = \\text{{Plani KG}} \\times \\text{{Çmimi (i Fundit ose Mesatar)}}$$
        """)

    st.divider()

    # --- METRIKAT ---
    t_kg_plan = gp["Plani_KG"].sum()
    t_v_plan = gp["Vlera_Planifikuar"].sum()
    kliente_pasive_num = len(df_pasive_baze) if not df_pasive_baze.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Plani KG Totale (Bonus)", f"{t_kg_plan:,.0f}")
    c2.metric("Klientë Aktivë", f"{gp['Klienti'].nunique():,}")
    c3.metric("Klientë Pasivë", f"{kliente_pasive_num:,}")
    c4.metric("Vlera Totale Plani", f"{t_v_plan:,.0f} L")

    st.divider()

    # --- TABET E DETAJEVE SIPAS KATEGORIVE, AGJENTËVE DHE KLIENTËVE PASIVË ---
    if klientet_selected:
        st.subheader("📍 Detajet e Artikujve për Klientët e Përzgjedhur")
        st.dataframe(
            gp[
                [
                    "Klienti",
                    "kat",
                    "NenKatZyrtare",
                    "Artikulli",
                    "Plani_KG",
                    "Vlera_Planifikuar",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        t1, t2, t3, t4 = st.tabs(
            ["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët", "💤 Klientët Pasivë"]
        )
        with t1:
            df_k = (
                gp.groupby("kat")
                .agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum"})
                .reset_index()
            )
            st.dataframe(
                df_k.sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
            )
        with t2:
            df_a = (
                gp.groupby("ForcaShitese")
                .agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum"})
                .reset_index()
            )
            st.dataframe(
                df_a.sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
            )
        with t3:
            df_kl = (
                gp.groupby(["Klienti", "ForcaShitese"])
                .agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum"})
                .reset_index()
            )
            st.dataframe(
                df_kl.sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
            )
        with t4:
            if not df_pasive_baze.empty:
                st.dataframe(
                    df_pasive_baze[
                        [
                            "Klienti",
                            "ForcaShitese",
                            "Data_Blerjes_Fundit",
                            "Muaj_Pa_Blerje",
                        ]
                    ].sort_values("Muaj_Pa_Blerje", ascending=False),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.success("Nuk ka klientë pasivë për këtë përzgjedhje!")

    # =========================================================
    # PJESA E DYTË: MATRICA E TRANSPOZUAR DHE PDF-të
    # =========================================================
    st.divider()
    st.subheader("🔄 Matrica e Transpozuar Zyrtare (Sipas Agjentëve)")

    if not gp.empty:
        df_matrica_transpozuar = gp.pivot_table(
            index="NenKatZyrtare",
            columns="ForcaShitese",
            values="Plani_KG",
            aggfunc="sum",
            fill_value=0,
        )

        renditje_finale_rreshtave = [
            nk for nk in nen_kat_renditja if nk in df_matrica_transpozuar.index
        ]
        if "VAJ" in df_matrica_transpozuar.index:
            renditje_finale_rreshtave.append("VAJ")

        df_matrica_transpozuar = df_matrica_transpozuar.reindex(
            renditje_finale_rreshtave
        )
        st.dataframe(df_matrica_transpozuar, width="stretch")

    # --- 📂 GENERATORI I PDF-VE TË TRANSPOZUARA ---
    st.divider()
    st.subheader("📂 Shkarko Planet e Transpozuara në PDF (Formati Adnan Elezi)")

    import io
    import zipfile
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    if not gp.empty:
        tot_deka_baza = gp[~gp["NenKatZyrtare"].isin(["VAJ"])]["Plani_KG"].sum()
        tot_vaj_baza = gp[gp["NenKatZyrtare"] == "VAJ"]["Plani_KG"].sum()

        koef_deka_paga = 270000 / tot_deka_baza if tot_deka_baza > 0 else 0.85
        koef_vaj_paga = 300000 / tot_vaj_baza if tot_vaj_baza > 0 else 0.80

        agjentet_unikë = gp["ForcaShitese"].unique()
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            sukses_count = 0

            for agjent in agjentet_unikë:
                df_agj = gp[gp["ForcaShitese"] == agjent].copy()
                if df_agj.empty:
                    continue

                emri_agjentit = str(agjent)
                kodi_agjentit = str(df_agj[kolona_kodi_agj_sql].iloc[0])
                rajoni_agjentit = str(df_agj[kolona_rajoni_sql].iloc[0])

                emri_fajlit = f"{kodi_agjentit}_{emri_agjentit}_{rajoni_agjentit}_{muaji_i_zgjedhur}.pdf".replace(
                    " ", "_"
                )
                nr_klienteve_aktuale = df_agj["Klienti"].nunique()

                df_agj_agreguar = (
                    df_agj.groupby("NenKatZyrtare")["Plani_KG"].sum().to_dict()
                )

                pdf_buffer = io.BytesIO()
                doc = SimpleDocTemplate(
                    pdf_buffer,
                    pagesize=letter,
                    rightMargin=40,
                    leftMargin=40,
                    topMargin=40,
                    bottomMargin=40,
                )
                story = []
                styles = getSampleStyleSheet()

                style_header = ParagraphStyle(
                    "HStyle",
                    parent=styles["Normal"],
                    fontSize=12,
                    fontName="Helvetica-Bold",
                    textColor=colors.white,
                )
                style_cell = ParagraphStyle(
                    "CStyle", parent=styles["Normal"], fontSize=10, leading=12
                )
                style_cell_bold = ParagraphStyle(
                    "CBStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    leading=12,
                )
                style_cell_right = ParagraphStyle(
                    "CRStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    alignment=2,
                    leading=12,
                )
                style_cell_right_bold = ParagraphStyle(
                    "CRBStyle",
                    parent=styles["Normal"],
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    alignment=2,
                    leading=12,
                )

                # Header PDF
                tabela_header_data = [
                    [
                        Paragraph(
                            f"PLANI SHITJES &nbsp;&nbsp;&nbsp;&nbsp; {muaji_i_zgjedhur.upper()} {viti_i_zgjedhur}",
                            style_header,
                        ),
                        "",
                    ],
                    [
                        Paragraph(
                            f"Agjenti i shitjes: <font color='red'><b>{emri_agjentit}</b></font>",
                            style_cell,
                        ),
                        Paragraph(
                            f"Kodi i agjentit: <b>{kodi_agjentit}</b>", style_cell
                        ),
                    ],
                    [
                        Paragraph("", style_cell),
                        Paragraph(
                            f"Rajoni i shitjes: <font color='blue'><b>{rajoni_agjentit}</b></font>",
                            style_cell,
                        ),
                    ],
                    [
                        Paragraph(
                            f"NR. TOTAL I KLIENTEVE: <b>{nr_klienteve_aktuale}</b>",
                            style_cell,
                        ),
                        "",
                    ],
                    [
                        Paragraph(
                            f"NR. I KLIENTEVE TE MUAJIT TE KALUAR: <b>{int(nr_klienteve_aktuale * 1.2)}</b>",
                            style_cell,
                        ),
                        "",
                    ],
                    [
                        Paragraph(
                            "NR. I PLANIFIKUAR I KLIENTEVE: __________________",
                            style_cell,
                        ),
                        "",
                    ],
                ]

                tabela_header = Table(tabela_header_data, colWidths=[265, 265])
                tabela_header.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                            ("SPAN", (0, 0), (1, 0)),
                            ("SPAN", (0, 3), (1, 3)),
                            ("SPAN", (0, 4), (1, 4)),
                            ("SPAN", (0, 5), (1, 5)),
                            ("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ("GRID", (0, 3), (-1, -1), 1, colors.black),
                            ("PADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(tabela_header)
                story.append(Spacer(1, 20))

                # Tabela e Transpozuar në PDF
                tabela_plan_data = [
                    [
                        Paragraph("", style_cell_bold),
                        Paragraph(
                            "<b>SASIA (KG)<br/>PER PAGEN</b>", style_cell_right_bold
                        ),
                        Paragraph(
                            "<b>SASIA (KG)<br/>PER BONUS</b>", style_cell_right_bold
                        ),
                    ]
                ]

                deka_bonus_tot = sum(
                    v for k, v in df_agj_agreguar.items() if k != "VAJ"
                )
                deka_paga_tot = deka_bonus_tot * koef_deka_paga

                tabela_plan_data.append(
                    [
                        Paragraph("<b>DEKA</b>", style_cell_bold),
                        Paragraph(
                            f"<b>{deka_paga_tot:,.0f}</b>", style_cell_right_bold
                        ),
                        Paragraph(
                            f"<b>{deka_bonus_tot:,.0f}</b>", style_cell_right_bold
                        ),
                    ]
                )

                for nk in nen_kat_renditja:
                    bonus_v = df_agj_agreguar.get(nk, 0)
                    paga_v = bonus_v * koef_deka_paga if bonus_v > 0 else 0

                    tabela_plan_data.append(
                        [
                            Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{nk}", style_cell),
                            Paragraph(
                                f"{paga_v:,.0f}" if paga_v > 0 else "-",
                                style_cell_right,
                            ),
                            Paragraph(
                                f"{bonus_v:,.0f}" if bonus_v > 0 else "-",
                                style_cell_right,
                            ),
                        ]
                    )

                vaj_bonus_tot = df_agj_agreguar.get("VAJ", 0)
                vaj_paga_tot = vaj_bonus_tot * koef_vaj_paga

                tabela_plan_data.append(
                    [
                        Paragraph("<b>VAJ</b>", style_cell_bold),
                        Paragraph(f"<b>{vaj_paga_tot:,.0f}</b>", style_cell_right_bold),
                        Paragraph(
                            f"<b>{vaj_bonus_tot:,.0f}</b>", style_cell_right_bold
                        ),
                    ]
                )

                tabela_plan = Table(tabela_plan_data, colWidths=[230, 150, 150])
                tabela_plan.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F8")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                            ("BOX", (0, 0), (-1, -1), 1, colors.black),
                            ("PADDING", (0, 0), (-1, -1), 4),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LINEBELOW", (0, 1), (-1, 1), 1.5, colors.black),
                            ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.black),
                        ]
                    )
                )
                story.append(tabela_plan)

                doc.build(story)
                zip_file.writestr(emri_fajlit, pdf_buffer.getvalue())
                sukses_count += 1

        zip_buffer.seek(0)
        st.download_button(
            label=f"🚀 Shkarko {sukses_count} PDF të Transpozuara (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"Planet_Zyrtare_Te_Transpozuara_{muaji_i_zgjedhur}.zip",
            mime="application/zip",
            type="primary",
        )

    # Excel Export
    st.sidebar.markdown("### 📥 Eksporte të tjera")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        gp.to_excel(writer, sheet_name="Plani", index=False)
    st.sidebar.download_button(
        label="📊 Shkarko Excel",
        data=buffer.getvalue(),
        file_name=f"Plani_{muaji_i_zgjedhur}.xlsx",
    )

# ---------------------------------------------------------
# MODULI: REALIZIMI
# ---------------------------------------------------------
elif page == "Realizimi":
    import numpy as np
    from datetime import datetime

    tani = datetime.now()

    # --- RREGULLIMI I STATE-IT PËR KTHIMIN LIVE ---
    if "tipi_muaji" not in st.session_state:
        st.session_state.tipi_muaji = "Muaji Korrent (Live)"

    # --- PANEL PERZGJDHJEJE DIREKT NË FAQE ---
    st.subheader("📅 Përzgjedhja e Periudhës së Analizës")

    col_p1, col_p2, col_p3 = st.columns([2, 2, 2])

    with col_p1:
        tipi_muaji = st.radio(
            "Mënyra e shfaqjes:",
            ["Muaji Korrent (Live)", "Muaj Specifik (Historik)"],
            key=(
                "tipi_muaji_radio"
                if st.session_state.tipi_muaji == "Muaj Specifik (Historik)"
                else None
            ),
            index=0 if st.session_state.tipi_muaji == "Muaji Korrent (Live)" else 1,
        )
        st.session_state.tipi_muaji = tipi_muaji

    # Variabël ndihmës për të kontrolluar nëse jemi në muajin korrent aktual
    eshte_muaji_korrent = True

    if st.session_state.tipi_muaji == "Muaji Korrent (Live)":
        sot = tani
        st.title(f"Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")
    else:
        lista_muajve = list(muajt_sq.keys())
        muaji_emer_list = [muajt_sq[m] for m in lista_muajve]

        with col_p2:
            me_perzgjedhur = st.selectbox(
                "Zgjidh Muajin:", muaji_emer_list, index=tani.month - 1
            )
        with col_p3:
            viti_perzgjedhur = st.selectbox(
                "Zgjidh Vitin:", range(tani.year - 2, tani.year + 2), index=2
            )

        muaji_numert = [k for k, v in muajt_sq.items() if v == me_perzgjedhur][0]

        if viti_perzgjedhur == tani.year and muaji_numert == tani.month:
            sot = tani
            st.title(f"Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")
        else:
            sot = datetime(viti_perzgjedhur, muaji_numert, 1) + pd.offsets.MonthEnd(0)
            st.title(f"Realizimi - {muajt_sq.get(sot.month)} {sot.year}")
            eshte_muaji_korrent = False  # Përdoruesi ka zgjedhur një muaj historik

        if st.button("🔄 Rikthe te Realizimi Live", use_container_width=True):
            st.session_state.tipi_muaji = "Muaji Korrent (Live)"
            st.rerun()

    # st.markdown(f"### 👤 Agjenti: **{agj_sel}**")
    st.divider()
    # ... (pjesa e përzgjedhjes së periudhës dhe përcaktimit të variablit 'sot' dhe st.title)

    # --- PËRGATITJA E TEKSTIT PËR KLIENTËT E ZGJEDHUR ---
    if klientet_selected:
        # Nëse janë zgjedhur më shumë se 5 klientë, shfaqim numrin e tyre që të mos bllokohet ekrani me tekst
        if len(klientet_selected) > 5:
            klientet_shfaq = f"{len(klientet_selected)} Klientë të përzgjedhur"
        else:
            klientet_shfaq = ", ".join(klientet_selected)
    else:
        klientet_shfaq = "Të gjithë"

    # --- SHFAQJA E FILTRAVE AKTIVË POSHTË TITULLIT ---
    col_info1, col_info2, col_info3 = st.columns(3)

    with col_info1:
        st.markdown(f"👤 Agjenti: **{agj_sel}**")
    with col_info2:
        st.markdown(f"📦 Grupi/Kategoria: **{grup_sel}**")
    with col_info3:
        st.markdown(f"🏪 Klienti: **{klientet_shfaq}**")

    st.divider()

    if df_raw is not None:
        # --- 1. TARGETI DHE REALIZIMI KORRENT ---
        mask_ref = (df_raw["Data"].dt.date >= start_date) & (
            df_raw["Data"].dt.date <= end_date
        )
        dff_ref = df_raw.loc[mask_ref].copy()
        if grup_sel != "Të gjitha":
            dff_ref = dff_ref[dff_ref["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            dff_ref = dff_ref[dff_ref["ForcaShitese"] == agj_sel]
        if klientet_selected:
            dff_ref = dff_ref[dff_ref["Klienti"].isin(klientet_selected)]

        n_months_ref = max(
            1,
            (end_date.year - start_date.year) * 12
            + (end_date.month - start_date.month),
        )
        rritja_faktori = 1 + (rritja / 100)

        # Targeti në KG
        gp_target_cat = dff_ref.groupby(["kat"]).agg({"kg": "sum"}).reset_index()
        gp_target_cat["KG_Target"] = (
            gp_target_cat["kg"] / n_months_ref
        ) * rritja_faktori
        t_target = gp_target_cat["KG_Target"].sum()

        # --- LLOGARITJA E PLANIT REAL TË KLIENTËVE DHE KODEVE ---
        dff_ref["Viti_Muaji"] = dff_ref["Data"].dt.to_period("M")

        kliente_per_muaj = dff_ref.groupby("Viti_Muaji")["Klienti"].nunique()
        mesatarja_kliente_ref = (
            kliente_per_muaj.mean() if not kliente_per_muaj.empty else 0
        )
        plan_kliente = max(1, round(mesatarja_kliente_ref * rritja_faktori))

        kode_per_muaj = dff_ref.groupby("Viti_Muaji")["KodiArt"].nunique()
        mesatarja_kode_ref = kode_per_muaj.mean() if not kode_per_muaj.empty else 0
        plan_kode = max(1, round(mesatarja_kode_ref * rritja_faktori))

        # --- FILTRIMI I MUAJIT TË PËRZGJEDHUR ---
        mask_live = (df_raw["Data"].dt.year == sot.year) & (
            df_raw["Data"].dt.month == sot.month
        )
        df_live = df_raw[mask_live].copy()
        if grup_sel != "Të gjitha":
            df_live = df_live[df_live["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_live = df_live[df_live["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_live = df_live[df_live["Klienti"].isin(klientet_selected)]

        t_real = df_live["kg"].sum()

        # --- REALIZIMI AKTUAL DISTINCT (KLIENTË DHE KODE) ---
        real_kliente = df_live["Klienti"].nunique()
        real_kode = df_live["KodiArt"].nunique()

        # --- LLOGARITJA E ÇMIMIT MESATAR ---
        t_vlera_live = (
            df_live["Vlera_Historike"].sum()
            if "Vlera_Historike" in df_live.columns
            else 0
        )
        if t_real > 0:
            cmimi_mesatar = t_vlera_live / t_real
        else:
            cmimi_mesatar = 0

        # --- 2. DITËT E PUNËS (Pa të diela) ---
        start_muaji = sot.replace(day=1)
        fund_muaji = start_muaji + pd.offsets.MonthEnd(0)
        ditet_punes_deri_sot = len(
            [d for d in pd.date_range(start_muaji, sot) if d.weekday() < 6]
        )
        ditet_punes_totale = len(
            [d for d in pd.date_range(start_muaji, fund_muaji) if d.weekday() < 6]
        )
        koha_perq = (
            (ditet_punes_deri_sot / ditet_punes_totale * 100)
            if ditet_punes_totale > 0
            else 0
        )

        # --- 3. METRIKAT KRYESORE (DINAMIKE SIPAS MUAJIT) ---
        if eshte_muaji_korrent:
            # Shfaqen të 7 metrikat nëse është muaji aktual/live
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

            c1.metric("Target KG", f"{t_target:,.0f}")
            c2.metric("Realizuar KG", f"{t_real:,.0f}")

            status_color = (
                "normal"
                if (t_real / t_target * 100 if t_target > 0 else 0) >= koha_perq
                else "inverse"
            )
            total_perc = (t_real / t_target * 100) if t_target > 0 else 0
            c3.metric(
                "Realizimi %",
                f"{total_perc:.1f}%",
                delta=f"{total_perc - koha_perq:.1f}% vs Koha",
                delta_color=status_color,
            )

            perc_kliente = (
                (real_kliente / plan_kliente * 100) if plan_kliente > 0 else 0
            )
            c4.metric(
                "Klientë Realiz/Plan",
                f"{real_kliente}/{plan_kliente}",
                f"{perc_kliente:.1f}%",
            )

            perc_kode = (real_kode / plan_kode * 100) if plan_kode > 0 else 0
            c5.metric(
                "Kode Unitare R/P", f"{real_kode}/{plan_kode}", f"{perc_kode:.1f}%"
            )

            c6.metric(
                "Ditë Pune",
                f"{ditet_punes_deri_sot}/{ditet_punes_totale}",
                f"{koha_perq:.1f}% e muajit",
            )
            c7.metric("Çmimi Mes./kg", f"{cmimi_mesatar:,.1f} Lekë")
        else:
            # Nëse është muaj historik, fshehim Target KG dhe Realizimi % (mbeten 5 metrika)
            c1, c2, c3, c4, c5 = st.columns(5)

            c1.metric("Realizuar KG", f"{t_real:,.0f}")

            perc_kliente = (
                (real_kliente / plan_kliente * 100) if plan_kliente > 0 else 0
            )
            c2.metric(
                "Klientë Realiz/Plan",
                f"{real_kliente}/{plan_kliente}",
                f"{perc_kliente:.1f}%",
            )

            perc_kode = (real_kode / plan_kode * 100) if plan_kode > 0 else 0
            c3.metric(
                "Kode Unitare R/P", f"{real_kode}/{plan_kode}", f"{perc_kode:.1f}%"
            )

            c4.metric("Ditë Pune Totale", f"{ditet_punes_totale}", "Muaj i mbyllur")
            c5.metric("Çmimi Mes./kg", f"{cmimi_mesatar:,.1f} Lekë")

        st.divider()

        # --- 4. ANALIZA E TRENDËVE (SHFAQET VETËM PËR MUAJIN KORRENT) ---
        # Krijojmë variablat paraprakisht që raporti HTML të mos dështojë kur eksportohet historiku
        ritmi_punes = t_real / ditet_punes_deri_sot if ditet_punes_deri_sot > 0 else 0
        projeksioni = ritmi_punes * ditet_punes_totale

        m_kaluar_date = sot - pd.DateOffset(months=1)
        mask_m = (
            (df_raw["Data"].dt.year == m_kaluar_date.year)
            & (df_raw["Data"].dt.month == m_kaluar_date.month)
            & (df_raw["Data"].dt.day <= sot.day)
        )
        df_m_kaluar = df_raw[mask_m].copy()
        if grup_sel != "Të gjitha":
            df_m_kaluar = df_m_kaluar[df_m_kaluar["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_m_kaluar = df_m_kaluar[df_m_kaluar["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_m_kaluar = df_m_kaluar[df_m_kaluar["Klienti"].isin(klientet_selected)]
        t_m_kaluar = df_m_kaluar["kg"].sum()
        rritja_m = ((t_real / t_m_kaluar) - 1) * 100 if t_m_kaluar > 0 else 0

        v_kaluar_date = sot - pd.DateOffset(years=1)
        mask_v = (
            (df_raw["Data"].dt.year == v_kaluar_date.year)
            & (df_raw["Data"].dt.month == v_kaluar_date.month)
            & (df_raw["Data"].dt.day <= sot.day)
        )
        df_v_kaluar = df_raw[mask_v].copy()
        if grup_sel != "Të gjitha":
            df_v_kaluar = df_v_kaluar[df_v_kaluar["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_v_kaluar = df_v_kaluar[df_v_kaluar["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_v_kaluar = df_v_kaluar[df_v_kaluar["Klienti"].isin(klientet_selected)]
        t_v_kaluar = df_v_kaluar["kg"].sum()
        rritja_v = ((t_real / t_v_kaluar) - 1) * 100 if t_v_kaluar > 0 else 0

        if eshte_muaji_korrent:
            st.subheader("🔍 Analiza e Trendeve (Krahasim me të njëjtën periudhë)")
            tr1, tr2, tr3 = st.columns(3)

            tr1.metric(
                "Trendi Linear",
                f"{projeksioni:,.0f} kg",
                delta=f"{projeksioni - t_target:,.0f} vs Plani",
            )
            tr2.metric(
                "vs Muaji Kaluar", f"{t_m_kaluar:,.0f} kg", delta=f"{rritja_m:.1f}%"
            )
            tr3.metric(
                "vs Viti Kaluar", f"{t_v_kaluar:,.0f} kg", delta=f"{rritja_v:.1f}%"
            )
            st.divider()

        # --- TABET E REALIZIMIT ---
        # Përgatisim të dhënat e agreguara për kategoritë (përfshirë vlerën për çmimin mesatar)
        df_comp = gp_target_cat.copy()
        gp_kat_live = df_live.groupby("kat", as_index=False).agg(
            KG_Real=("kg", "sum"),
            Vlera_Real=(
                ("Vlera_Historike", "sum")
                if "Vlera_Historike" in df_live.columns
                else ("kg", lambda x: 0)
            ),
        )

        df_comp = pd.merge(
            df_comp[["kat", "KG_Target"]],
            gp_kat_live,
            on="kat",
            how="left",
        ).fillna(0)

        # Llogarisim çmimin mesatar për kategoritë
        df_comp["Cmimi_Mesatar"] = np.where(
            df_comp["KG_Real"] > 0, df_comp["Vlera_Real"] / df_comp["KG_Real"], 0
        )

        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])

        with t1:
            st.subheader("Ecuria sipas Kategorive")
            if eshte_muaji_korrent:
                df_comp["Progresi"] = (
                    df_comp["KG_Real"] / df_comp["KG_Target"] * 100
                ).clip(upper=100)
                kolonat_shfaq = [
                    "kat",
                    "KG_Target",
                    "KG_Real",
                    "Progresi",
                    "Cmimi_Mesatar",
                ]
                konfigurimi_kolonave = {
                    "kat": "Kategoria",
                    "KG_Target": st.column_config.NumberColumn(
                        "Target (KG)", format="%d"
                    ),
                    "KG_Real": st.column_config.NumberColumn(
                        "Realizuar (KG)", format="%d"
                    ),
                    "Progresi": st.column_config.ProgressColumn(
                        "Ecuria %", min_value=0, max_value=100, format="%.1f%%"
                    ),
                    "Cmimi_Mesatar": st.column_config.NumberColumn(
                        "Çmimi Mes. (Lekë/kg)", format="%.1f"
                    ),
                }
            else:
                kolonat_shfaq = ["kat", "KG_Real", "Cmimi_Mesatar"]
                konfigurimi_kolonave = {
                    "kat": "Kategoria",
                    "KG_Real": st.column_config.NumberColumn(
                        "Realizuar (KG)", format="%d"
                    ),
                    "Cmimi_Mesatar": st.column_config.NumberColumn(
                        "Çmimi Mes. (Lekë/kg)", format="%.1f"
                    ),
                }

            st.dataframe(
                df_comp[kolonat_shfaq],
                column_config=konfigurimi_kolonave,
                hide_index=True,
                use_container_width="stretch",
            )

        with t2:
            st.subheader("Ecuria sipas Agjentëve")
            gp_agj_live = (
                df_live.groupby("ForcaShitese")
                .agg(
                    Real_AGJ=("kg", "sum"),
                    Vlera_AGJ=(
                        ("Vlera_Historike", "sum")
                        if "Vlera_Historike" in df_live.columns
                        else ("kg", lambda x: 0)
                    ),
                )
                .reset_index()
            )

            # Llogarisim çmimin mesatar për agjentët
            gp_agj_live["Cmimi_Mesatar"] = np.where(
                gp_agj_live["Real_AGJ"] > 0,
                gp_agj_live["Vlera_AGJ"] / gp_agj_live["Real_AGJ"],
                0,
            )

            if eshte_muaji_korrent:
                gp_agj_target = (
                    dff_ref.groupby("ForcaShitese").agg({"kg": "sum"}).reset_index()
                )
                gp_agj_target["Target_AGJ"] = (
                    gp_agj_target["kg"] / n_months_ref
                ) * rritja_faktori
                df_agj = pd.merge(
                    gp_agj_target[["ForcaShitese", "Target_AGJ"]],
                    gp_agj_live,
                    on="ForcaShitese",
                    how="left",
                ).fillna(0)
                df_agj["%"] = (df_agj["Real_AGJ"] / df_agj["Target_AGJ"] * 100).clip(
                    upper=100
                )

                st.dataframe(
                    df_agj.sort_values("%", ascending=False),
                    column_config={
                        "ForcaShitese": "Agjenti",
                        "Target_AGJ": st.column_config.NumberColumn(
                            "Target", format="%d"
                        ),
                        "Real_AGJ": st.column_config.NumberColumn(
                            "Realizuar", format="%d"
                        ),
                        "%": st.column_config.ProgressColumn(
                            "Ecuria", min_value=0, max_value=100, format="%.1f%%"
                        ),
                        "Cmimi_Mesatar": st.column_config.NumberColumn(
                            "Çmimi Mes. (Lekë/kg)", format="%.1f"
                        ),
                    },
                    hide_index=True,
                    use_container_width="stretch",
                )
            else:
                st.dataframe(
                    gp_agj_live.sort_values("Real_AGJ", ascending=False)[
                        ["ForcaShitese", "Real_AGJ", "Cmimi_Mesatar"]
                    ],
                    column_config={
                        "ForcaShitese": "Agjenti",
                        "Real_AGJ": st.column_config.NumberColumn(
                            "Realizuar Total (KG)", format="%d"
                        ),
                        "Cmimi_Mesatar": st.column_config.NumberColumn(
                            "Çmimi Mes. (Lekë/kg)", format="%.1f"
                        ),
                    },
                    hide_index=True,
                    use_container_width="stretch",
                )

        with t3:
            st.subheader("Ecuria sipas Klientëve")
            gp_kl_live = (
                df_live.groupby("Klienti")
                .agg(
                    Real_KL=("kg", "sum"),
                    Vlera_KL=(
                        ("Vlera_Historike", "sum")
                        if "Vlera_Historike" in df_live.columns
                        else ("kg", lambda x: 0)
                    ),
                )
                .reset_index()
            )

            # Llogarisim çmimin mesatar për klientët
            gp_kl_live["Cmimi_Mesatar"] = np.where(
                gp_kl_live["Real_KL"] > 0,
                gp_kl_live["Vlera_KL"] / gp_kl_live["Real_KL"],
                0,
            )

            if eshte_muaji_korrent:
                gp_kl_target = (
                    dff_ref.groupby(["Klienti", "ForcaShitese"])
                    .agg({"kg": "sum"})
                    .reset_index()
                )
                gp_kl_target["Target_KL"] = (
                    gp_kl_target["kg"] / n_months_ref
                ) * rritja_faktori
                df_kl = pd.merge(
                    gp_kl_target[["Klienti", "ForcaShitese", "Target_KL"]],
                    gp_kl_live,
                    on="Klienti",
                    how="left",
                ).fillna(0)
                df_kl["%"] = (df_kl["Real_KL"] / df_kl["Target_KL"] * 100).clip(
                    upper=100
                )
                df_kl = df_kl[df_kl["Target_KL"] > 0]

                st.dataframe(
                    df_kl.sort_values("%", ascending=False),
                    column_config={
                        "Klienti": "Klienti",
                        "ForcaShitese": "Agjenti",
                        "Target_KL": st.column_config.NumberColumn(
                            "Target", format="%d"
                        ),
                        "Real_KL": st.column_config.NumberColumn(
                            "Realizuar", format="%d"
                        ),
                        "%": st.column_config.ProgressColumn(
                            "Ecuria", min_value=0, max_value=100, format="%.1f%%"
                        ),
                        "Cmimi_Mesatar": st.column_config.NumberColumn(
                            "Çmimi Mes. (Lekë/kg)", format="%.1f"
                        ),
                    },
                    hide_index=True,
                    use_container_width="stretch",
                )
            else:
                gp_kl_agj = (
                    df_live.groupby(["Klienti", "ForcaShitese"])
                    .agg(
                        Real_KL=("kg", "sum"),
                        Vlera_KL=(
                            ("Vlera_Historike", "sum")
                            if "Vlera_Historike" in df_live.columns
                            else ("kg", lambda x: 0)
                        ),
                    )
                    .reset_index()
                )

                gp_kl_agj["Cmimi_Mesatar"] = np.where(
                    gp_kl_agj["Real_KL"] > 0,
                    gp_kl_agj["Vlera_KL"] / gp_kl_agj["Real_KL"],
                    0,
                )

                st.dataframe(
                    gp_kl_agj.sort_values("Real_KL", ascending=False),
                    column_config={
                        "Klienti": "Klienti",
                        "ForcaShitese": "Agjenti",
                        "Real_KL": st.column_config.NumberColumn(
                            "Realizuar (KG)", format="%d"
                        ),
                        "Cmimi_Mesatar": st.column_config.NumberColumn(
                            "Çmimi Mes. (Lekë/kg)", format="%.1f"
                        ),
                    },
                    hide_index=True,
                    use_container_width="stretch",
                )

        # --- 7. EKSPORTI NË HTML ---
        st.divider()

        agj_emri_fajl = (
            agj_sel.replace(" ", "_") if agj_sel != "Të gjithë" else "Gjithe_Agjentet"
        )
        file_name_custom = f"Raport_{agj_emri_fajl}_{sot.strftime('%d_%m_%Y')}.html"
        klientet_text = (
            ", ".join(klientet_selected) if klientet_selected else "Të gjithë"
        )

        cls_proj = "positive" if projeksioni >= t_target else "negative"
        cls_m = "positive" if rritja_m >= 0 else "negative"
        cls_v = "positive" if rritja_v >= 0 else "negative"

        # Krijimi i seksioneve specifike për bllokun HTML bazuar në llojin e muajit
        html_target_box = (
            f'<div class="stat-box"><h3>Targeti (Muaj)</h3><p>{t_target:,.0f} kg</p></div>'
            if eshte_muaji_korrent
            else ""
        )
        html_perc_box = (
            f'<div class="stat-box"><h3>Ecuria %</h3><p>{(t_real / t_target * 100 if t_target > 0 else 0):.1f}%</p></div>'
            if eshte_muaji_korrent
            else ""
        )
        html_days_title = (
            "Statusi i Kohës" if eshte_muaji_korrent else "Ditë Pune Totale"
        )
        html_days_value = (
            f"{ditet_punes_deri_sot}/{ditet_punes_totale} Ditë"
            if eshte_muaji_korrent
            else f"{ditet_punes_totale} Ditë"
        )

        html_trend_table = (
            f"""
        <div class="trend-section">
            <h2 style="margin-top:0; color: #1a237e; font-size: 18px;">🔍 Krahasimi i Trendeve (Pa të diela)</h2>
            <table>
                <thead>
                    <tr><th>Lloji i Trendit</th><th>Vlera e Krahasuar</th><th>Devijimi / Rritja</th></tr>
                </thead>
                <tbody>
                    <tr><td><strong>Trendi Linear</strong> (Parashikimi i mbylljes)</td><td>{projeksioni:,.0f} kg</td><td class="{cls_proj}">{projeksioni - t_target:,.0f} kg vs Objektivi</td></tr>
                    <tr><td><strong>vs Muaji i Kaluar</strong> (Deri në datën {sot.day})</td><td>{t_m_kaluar:,.0f} kg</td><td class="{cls_m}">{rritja_m:+.1f}%</td></tr>
                    <tr><td><strong>vs Viti i Kaluar</strong> (Deri në datën {sot.day})</td><td>{t_v_kaluar:,.0f} kg</td><td class="{cls_v}">{rritja_v:+.1f}%</td></tr>
                </tbody>
            </table>
        </div>
        """
            if eshte_muaji_korrent
            else ""
        )

        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #f8f9fa; color: #333; }}
                .header {{ background-color: #1a237e; color: white; padding: 25px; border-radius: 12px 12px 0 0; text-align: center; }}
                .filter-bar {{ background-color: #ffffff; padding: 15px; border: 1px solid #e0e0e0; font-size: 13px; display: flex; flex-wrap: wrap; gap: 20px; }}
                .filter-item {{ color: #555; }}
                .filter-item strong {{ color: #1a237e; }}
                .stats-container {{ display: flex; justify-content: space-between; margin: 20px 0; gap: 10px; flex-wrap: wrap; }}
                .stat-box {{ background: white; padding: 15px 10px; border-radius: 10px; border-bottom: 4px solid #1a237e; min-width: 12%; flex-grow: 1; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                .stat-box h3 {{ margin: 0; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #777; }}
                .stat-box p {{ font-size: 16px; font-weight: bold; margin: 10px 0; color: #1a237e; }}
                .trend-section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #eee; }}
                th {{ background-color: #fcfcfc; font-weight: 600; color: #555; }}
                .positive {{ color: #2e7d32; font-weight: bold; }}
                .negative {{ color: #c62828; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 40px; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin:0;">{"Analiza e Realizimit Live" if eshte_muaji_korrent else "Analiza e Realizimit"}: {muajt_sq.get(sot.month)} {sot.year}</h1>
                <p style="margin:10px 0 0 0; opacity: 0.8;">Raport zyrtar i performancës së shitjeve</p>
            </div>

            <div class="filter-bar">
                <div class="filter-item">Referenca: <strong>{start_date.strftime('%d/%m/%y')} - {end_date.strftime('%d/%m/%y')}</strong></div>
                <div class="filter-item">📈 Rritja e aplikuar: <strong>{rritja}%</strong></div>
                <div class="filter-item">📦 Grupi: <strong>{grup_sel}</strong></div>
                <div class="filter-item">👤 Agjenti: <strong>{agj_sel}</strong></div>
                <div class="filter-item">🏪 Klientët: <strong>{klientet_text}</strong></div>
            </div>

            <div class="stats-container">
                {html_target_box}
                <div class="stat-box"><h3>Realizuar KG</h3><p>{t_real:,.0f} kg</p></div>
                {html_perc_box}
                <div class="stat-box"><h3>Klientë R/P</h3><p>{real_kliente}/{plan_kliente}</p></div>
                <div class="stat-box"><h3>Kode R/P</h3><p>{real_kode}/{plan_kode}</p></div>
                <div class="stat-box"><h3>{html_days_title}</h3><p>{html_days_value}</p></div>
                <div class="stat-box"><h3>Çmimi Mesatar</h3><p>{cmimi_mesatar:,.2f} Lekë</p></div>
            </div>

            {html_trend_table}

            <div class="footer">
                Gjeneruar nga Sistemi i Monitorimit të Shitjeve | Data: {sot.strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </body>
        </html>
        """

        st.download_button(
            label=f"💾 Shkarko Raportin: {file_name_custom}",
            data=html_report,
            file_name=file_name_custom,
            mime="text/html",
            use_container_width=True,
        )

# ---------------------------------------------------------
# MODULI: MUNDESITE
# ---------------------------------------------------------
elif page == "Mundësitë":
    # st.title("🎯 Analiza e Mundësive (Gap Analysis)")
    st.title("Analiza e Mundësive (Gap Analysis)")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")
    # --- SEKSIONI INFO MBI LLOGARITJEN ---
    with st.expander("ℹ️ Si llogaritet ky vlerësim? (Metodologjia)"):
        st.write("""
            Ky modul përdor algoritmin **'Gap Analysis'** për të gjetur hapësirat bosh në shitje:
            
            1. **Periudha Historike:** Sistemi analizon të gjitha blerjet e klientit që nga fillimi deri 90 ditë para datës së sotme.
            2. **Periudha Aktuale:** Sistemi kontrollon faturat e 90 ditëve të fundit (3 muajt e fundit).
            3. **Identifikimi i Mundësisë:** Nëse një artikull është blerë në të shkuarën (Volum Historik > 0) por nuk figuron në asnjë faturë të 90 ditëve të fundit, ai listohet si **Mundësi**.
            4. **Renditja:** Artikujt renditen sipas **KG Historike**, në mënyrë që agjenti të fokusojë forcën te produktet që kanë peshën më të madhe në xhiro.
        """)

    if df_raw is not None:
        df_m = df_raw.copy()

        # FILTRI SPECIFIK: Këtu i heqim inaktivët
        df_m = df_m[df_m["statusi"].astype(str).str.upper() == "AKTIV"]

        # 1. Filtrat (Sigurohu që përdor variablat e saktë nga Sidebar)
        if agj_sel != "Të gjithë":
            df_m = df_m[df_m["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_m = df_m[df_m["Klienti"].isin(klientet_selected)]
        if grup_sel != "Të gjitha":
            df_m = df_m[df_m["Grup_Filtri"] == grup_sel]

        # 2. Logjika e Gap (90 ditë)
        sot = datetime.now()
        kufiri_aktual = sot - pd.Timedelta(days=90)

        shitjet_historike = df_m[df_m["Data"] < kufiri_aktual]
        shitjet_aktuale = df_m[df_m["Data"] >= kufiri_aktual]

        portfolio_hist = (
            shitjet_historike.groupby(["Klienti", "Artikulli", "kat"])
            .agg({"Data": "max", "kg": "sum"})
            .reset_index()
        )

        portfolio_akt = shitjet_aktuale[["Klienti", "Artikulli"]].drop_duplicates()
        portfolio_akt["Blerë_Aktualisht"] = True

        mundesite = pd.merge(
            portfolio_hist, portfolio_akt, on=["Klienti", "Artikulli"], how="left"
        )
        mundesite = mundesite[mundesite["Blerë_Aktualisht"].isna()].copy()

        if not mundesite.empty:
            # --- RREGULLIMI I GABIMIT (Formatimi paraprak) ---

            # Kthejmë datën në tekst që në fillim për të shmangur gabimin e Styler
            mundesite["Blerja e Fundit"] = mundesite["Data"].dt.strftime("%d/%m/%Y")

            # Përzgjedhim kolonat finale
            tabela_finale = mundesite[
                ["Klienti", "Artikulli", "kat", "Blerja e Fundit", "kg"]
            ].copy()
            tabela_finale.columns = [
                "Klienti",
                "Artikulli",
                "Kategoria",
                "Blerja e Fundit",
                "KG Historike",
            ]

            st.subheader(
                f"⚠️ Janë gjetur {len(tabela_finale)} raste potencialisht të humbura"
            )

            # Shfaqja e tabelës pa përdorur .style (më e sigurt)
            st.dataframe(
                tabela_finale.sort_values("KG Historike", ascending=False),
                use_container_width=True,
                height=500,
            )

            # Statistika
            c1, c2 = st.columns(2)
            with c1:
                top_k = tabela_finale.groupby("Klienti")["KG Historike"].sum().idxmax()
                st.metric("Klienti me më shumë potencial", top_k)
            with c2:
                top_a = (
                    tabela_finale.groupby("Artikulli")["KG Historike"].sum().idxmax()
                )
                st.metric("Artikulli më i harruar", top_a)
        else:
            st.success("✅ Nuk u gjet asnjë 'Gap' në shitje për këtë përzgjedhje.")


# ---------------------------------------------------------
# MODULI I PLOTË: SHITJET DITORE (ME PËRZGJEDHJE DINAMIKE TË PERIUDHAVE)
# ---------------------------------------------------------
elif page == "Shitjet Ditore":
    import calendar
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime

    # Data aktuale e sistemit
    sot = datetime.now()
    dita_korrente = sot.day

    st.title(f"Shitjet Ditore")

    # Shfaqja e datës së sotme ekzakte në raport
    st.markdown(
        f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #1a237e; margin-bottom: 15px;'>
            <h3 style='color: #1a237e; margin: 0; font-size: 20px;'>Raporti i Shitjeve Ditore Krahasuese</h3>
            <p style='margin: 5px 0 0 0; color: #666; font-size: 14px;'>
                📅 Data e gjenerimit të raportit: <strong>{sot.strftime('%d/%m/%Y')}</strong> | 👤 Agjenti: <strong>{agj_sel}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df_raw is not None and not df_raw.empty:

        kolona_kg = "kg"
        kolona_vlera = "Vlera_Historike"

        # --- PREGATITJA E DATASETIT BAZE ---
        df_base = df_raw.copy()
        df_base["Data"] = pd.to_datetime(df_base["Data"], errors="coerce")

        # Gjejmë vitet dhe muajt unikë në databazë për t'i dhënë si opsione zgjedhjeje
        vitet_disponueshme = sorted(
            list(df_base["Data"].dt.year.dropna().unique()), reverse=True
        )
        if sot.year not in vitet_disponueshme:
            vitet_disponueshme.insert(0, sot.year)

        # --- LLOGARITJA E PERIUDHAVE DEFAULT ---
        vit_aktual_def = sot.year
        muaj_aktual_def = sot.month

        if muaj_aktual_def == 1:
            vit_para_muaj_def = vit_aktual_def - 1
            para_muaj_def = 12
        else:
            vit_para_muaj_def = vit_aktual_def
            para_muaj_def = muaj_aktual_def - 1

        vit_para_vit_def = vit_aktual_def - 1
        para_vit_muaj_def = muaj_aktual_def

        # --- SEKSIONI I FILTRAVE TË PERIUDHAVE (SELECTION BOXES) ---
        st.markdown("##### 📅 Përzgjidhni periudhat për krahasim:")
        col_p1, col_p2, col_p3 = st.columns(3)

        with col_p1:
            st.markdown("**Grafiku 1 (Kryesor / Aktual)**")
            sel_muaj_1 = st.selectbox(
                "Muaji (G1)",
                list(muajt_sq.keys()),
                format_func=lambda x: muajt_sq[x],
                index=list(muajt_sq.keys()).index(muaj_aktual_def),
                key="m1",
            )
            sel_vit_1 = st.selectbox(
                "Viti (G1)",
                vitet_disponueshme,
                index=(
                    vitet_disponueshme.index(vit_aktual_def)
                    if vit_aktual_def in vitet_disponueshme
                    else 0
                ),
                key="v1",
            )

        with col_p2:
            st.markdown("**Grafiku 2 (Krahasues i parë)**")
            sel_muaj_2 = st.selectbox(
                "Muaji (G2)",
                list(muajt_sq.keys()),
                format_func=lambda x: muajt_sq[x],
                index=list(muajt_sq.keys()).index(para_muaj_def),
                key="m2",
            )
            sel_vit_2 = st.selectbox(
                "Viti (G2)",
                vitet_disponueshme,
                index=(
                    vitet_disponueshme.index(vit_para_muaj_def)
                    if vit_para_muaj_def in vitet_disponueshme
                    else 0
                ),
                key="v2",
            )

        with col_p3:
            st.markdown("**Grafiku 3 (Krahasues i dytë)**")
            sel_muaj_3 = st.selectbox(
                "Muaji (G3)",
                list(muajt_sq.keys()),
                format_func=lambda x: muajt_sq[x],
                index=list(muajt_sq.keys()).index(para_vit_muaj_def),
                key="m3",
            )
            sel_vit_3 = st.selectbox(
                "Viti (G3)",
                vitet_disponueshme,
                index=(
                    vitet_disponueshme.index(vit_para_vit_def)
                    if vit_para_vit_def in vitet_disponueshme
                    else 0
                ),
                key="v3",
            )

        # --- EMRAT DINAMIKË BAZUAR MBI ZGJEDHJET ---
        emri_muaj_1 = f"{muajt_sq.get(sel_muaj_1).upper()} {sel_vit_1}"
        emri_muaj_2 = f"{muajt_sq.get(sel_muaj_2).upper()} {sel_vit_2}"
        emri_muaj_3 = f"{muajt_sq.get(sel_muaj_3).upper()} {sel_vit_3}"

        # --- APLIKIMI I FILTRAVE TË TJERË (KLIENTË, AGJENTË, GRUPE) ---
        if grup_sel != "Të gjitha":
            df_base = df_base[df_base["Grup_Filtri"] == grup_sel]

        if agj_sel != "Të gjithë":
            df_base = df_base[df_base["ForcaShitese"] == agj_sel]

        if klientet_selected:
            df_base = df_base[df_base["Klienti"].isin(klientet_selected)]

        # --- FUNKSIONI I MARRJES SË TË DHËNAVE ---
        def merr_te_dhenat_mujore(df_filtri, vit, muaj):
            df_p = df_filtri[
                (df_filtri["Data"].dt.year == vit)
                & (df_filtri["Data"].dt.month == muaj)
            ].copy()
            if not df_p.empty:
                df_p["Dita_Numri"] = df_p["Data"].dt.day
                df_p[kolona_kg] = pd.to_numeric(
                    df_p[kolona_kg], errors="coerce"
                ).fillna(0)
                df_p[kolona_vlera] = pd.to_numeric(
                    df_p[kolona_vlera], errors="coerce"
                ).fillna(0)

                return (
                    df_p.groupby("Dita_Numri")
                    .agg({kolona_kg: "sum", kolona_vlera: "sum"})
                    .to_dict(orient="index")
                )
            return {}

        data_aktual = merr_te_dhenat_mujore(df_base, sel_vit_1, sel_muaj_1)
        data_para_muaj = merr_te_dhenat_mujore(df_base, sel_vit_2, sel_muaj_2)
        data_para_vit = merr_te_dhenat_mujore(df_base, sel_vit_3, sel_muaj_3)

        # Gjejmë numrin total të ditëve për secilin muaj të zgjedhur
        _, ditet_totale_m1 = calendar.monthrange(sel_vit_1, sel_muaj_1)
        _, ditet_totale_m2 = calendar.monthrange(sel_vit_2, sel_muaj_2)
        _, ditet_totale_m3 = calendar.monthrange(sel_vit_3, sel_muaj_3)

        # Ditët në boshtin X do të udhëhiqen nga muaji kryesor i zgjedhur (Grafiku 1)
        ditet_numerik = list(range(1, ditet_totale_m1 + 1))
        ditet_etiketa = [f"{d:02d}" for d in ditet_numerik]

        def llogarit_kaskaden_dhe_cmimin(data_dict, nr_dite_muaji):
            vlerat_reale = []
            vlerat_baze = []
            kumulativ = 0.0
            t_sasia = 0.0
            t_vlera = 0.0

            for d in range(1, nr_dite_muaji + 1):
                dita_data = data_dict.get(d, {kolona_kg: 0.0, kolona_vlera: 0.0})
                sasia = dita_data[kolona_kg]
                vlera = dita_data[kolona_vlera]

                vlerat_baze.append(kumulativ)
                vlerat_reale.append(sasia)
                kumulativ += sasia

                t_sasia += sasia
                t_vlera += vlera

            cmimi_mesatar = (t_vlera / t_sasia) if t_sasia > 0 else 0.0
            return vlerat_baze, vlerat_reale, cmimi_mesatar

        base_aktual, y_aktual, cm_mes_aktual = llogarit_kaskaden_dhe_cmimin(
            data_aktual, ditet_totale_m1
        )
        base_para_muaj, y_para_muaj, cm_mes_para_muaj = llogarit_kaskaden_dhe_cmimin(
            data_para_muaj, ditet_totale_m2
        )
        base_para_vit, y_para_vit, cm_mes_para_vit = llogarit_kaskaden_dhe_cmimin(
            data_para_vit, ditet_totale_m3
        )

        # --- LLOGARITJA E METRIKAVE LIKE-TO-LIKE ---
        def llogarit_kumulativ_deri_diten(data_dict, max_day, limit_muaji):
            sasia_kumulative = 0.0
            vlera_kumulative = 0.0
            kufiri_real = min(max_day, limit_muaji)

            for d in range(1, kufiri_real + 1):
                dita_data = data_dict.get(d, {kolona_kg: 0.0, kolona_vlera: 0.0})
                sasia_kumulative += dita_data.get(kolona_kg, 0.0)
                vlera_kumulative += dita_data.get(kolona_vlera, 0.0)

            cmimi_mesatar_periudhe = (
                (vlera_kumulative / sasia_kumulative) if sasia_kumulative > 0 else 0.0
            )
            return sasia_kumulative, cmimi_mesatar_periudhe

        totali_aktual = sum(y_aktual)
        totali_para_muaj_l2l, cm_mes_para_muaj_l2l = llogarit_kumulativ_deri_diten(
            data_para_muaj, dita_korrente, ditet_totale_m2
        )
        totali_para_vit_l2l, cm_mes_para_vit_l2l = llogarit_kumulativ_deri_diten(
            data_para_vit, dita_korrente, ditet_totale_m3
        )

        # --- LLOGARITJA E SASIVE MESATARE PËR DITË PUNE (Hënë - Shtunë) ---
        def llogarit_mesatare_dite_pune(vit, muaj, max_day, limit_muaji, data_dict):
            kufiri_real = min(max_day, limit_muaji)
            ditet_punes = [
                d
                for d in range(1, kufiri_real + 1)
                if datetime(vit, muaj, d).weekday() != 6
            ]
            nr_dite_pune = len(ditet_punes)
            sasia_totale_pune = sum(
                data_dict.get(d, {kolona_kg: 0.0})[kolona_kg] for d in ditet_punes
            )
            return (sasia_totale_pune / nr_dite_pune) if nr_dite_pune > 0 else 0.0

        # Llogaritja e mesatareve ditore operative dhe të plota
        mes_dite_l2l_m1 = llogarit_mesatare_dite_pune(
            sel_vit_1, sel_muaj_1, dita_korrente, ditet_totale_m1, data_aktual
        )
        mes_dite_l2l_m2 = llogarit_mesatare_dite_pune(
            sel_vit_2, sel_muaj_2, dita_korrente, ditet_totale_m2, data_para_muaj
        )
        mes_dite_l2l_m3 = llogarit_mesatare_dite_pune(
            sel_vit_3, sel_muaj_3, dita_korrente, ditet_totale_m3, data_para_vit
        )

        mes_dite_plote_m1 = llogarit_mesatare_dite_pune(
            sel_vit_1, sel_muaj_1, ditet_totale_m1, ditet_totale_m1, data_aktual
        )
        mes_dite_plote_m2 = llogarit_mesatare_dite_pune(
            sel_vit_2, sel_muaj_2, ditet_totale_m2, ditet_totale_m2, data_para_muaj
        )
        mes_dite_plote_m3 = llogarit_mesatare_dite_pune(
            sel_vit_3, sel_muaj_3, ditet_totale_m3, ditet_totale_m3, data_para_vit
        )

        # --- SHFAQJA E METRIKAVE ---
        st.markdown(
            "<h4 style='color: #2c3e50; font-size:18px; margin-top:15px; margin-bottom:15px;'>📊 Përmbledhje e Performancës Mujore</h4>",
            unsafe_allow_html=True,
        )

        # Rreshti 1: Volumet totale sipas përzgjedhjes
        c1, c2, c3 = st.columns(3)
        c1.metric(
            label=f"Sasia {emri_muaj_1}",
            value=f"{totali_aktual:,.0f} kg",
            delta=f"Ø Çmimi: {cm_mes_aktual:,.1f} L/kg",
            delta_color="off",
        )
        c2.metric(
            label=f"Sasia e Plotë {emri_muaj_2}",
            value=f"{sum(y_para_muaj):,.0f} kg",
            delta=f"Ø Çmimi: {cm_mes_para_muaj:,.1f} L/kg",
            delta_color="off",
        )
        c3.metric(
            label=f"Sasia e Plotë {emri_muaj_3}",
            value=f"{sum(y_para_vit):,.0f} kg",
            delta=f"Ø Çmimi: {cm_mes_para_vit:,.1f} L/kg",
            delta_color="off",
        )

        st.write("")
        # Rreshti 2: Krahasimi Like-to-Like deri në ditën korrente
        ndryshimi_m2_l2l = (
            ((totali_aktual - totali_para_muaj_l2l) / totali_para_muaj_l2l * 100)
            if totali_para_muaj_l2l > 0
            else 0
        )
        ndryshimi_m3_l2l = (
            ((totali_aktual - totali_para_vit_l2l) / totali_para_vit_l2l * 100)
            if totali_para_vit_l2l > 0
            else 0
        )

        cc1, cc2, cc3 = st.columns(3)
        cc1.markdown(
            f"<div style='text-align:center; background:#e9ecef; padding:12px; border-radius:6px; font-size:13px; font-weight:bold; color:#495057; margin-top:5px;'>Krahasimi Like-to-Like<br>(Deri në ditën {dita_korrente} pa të Diela)</div>",
            unsafe_allow_html=True,
        )
        cc2.metric(
            label=f"vs {emri_muaj_2} (Dita 1-{min(dita_korrente, ditet_totale_m2)})",
            value=f"{totali_para_muaj_l2l:,.0f} kg",
            delta=f"{ndryshimi_m2_l2l:+.1f}% (Ø: {cm_mes_para_muaj_l2l:,.1f} L)",
        )
        cc3.metric(
            label=f"vs {emri_muaj_3} (Dita 1-{min(dita_korrente, ditet_totale_m3)})",
            value=f"{totali_para_vit_l2l:,.0f} kg",
            delta=f"{ndryshimi_m3_l2l:+.1f}% (Ø: {cm_mes_para_vit_l2l:,.1f} L)",
        )

        st.write("")

        # Rreshti 3: Tabela e pastër e Mesatareve të zgjedhura
        st.markdown(
            "<h5 style='color: #2c3e50; font-size:15px; margin-top:15px; margin-bottom:10px;'>📈 Sasia Mesatare për Ditë Pune (Hënë - Shtunë, pa të Diela)</h5>",
            unsafe_allow_html=True,
        )

        status_m1_plote = (
            f"{mes_dite_plote_m1:,.0f} kg/ditë"
            if (
                sel_vit_1 < sot.year
                or (sel_vit_1 == sot.year and sel_muaj_1 < sot.month)
            )
            else "Muaj në progres"
        )

        html_tabela_mesatareve = f"""
        <table style="width:100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #1a237e; color: #ffffff; text-align: left; font-size: 14px;">
                    <th style="padding: 12px 15px;">Periudha / Muaji i Përzgjedhur</th>
                    <th style="padding: 12px 15px; text-align: center;">⏱️ Live (Dita 1-{dita_korrente})</th>
                    <th style="padding: 12px 15px; text-align: center;">🏁 Gjithë Muajin e Plotë</th>
                </tr>
            </thead>
            <tbody style="font-size: 14px; color: #333333;">
                <tr style="border-bottom: 1px solid #dddddd; background-color: #fcfcfd;">
                    <td style="padding: 12px 15px; font-weight: bold; color: #1a237e;">{emri_muaj_1}</td>
                    <td style="padding: 12px 15px; text-align: center; font-weight: bold; font-size: 16px; color: #2e7d32;">{mes_dite_l2l_m1:,.0f} kg/ditë</td>
                    <td style="padding: 12px 15px; text-align: center; color: #555;">{status_m1_plote}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dddddd;">
                    <td style="padding: 12px 15px; font-weight: bold;">{emri_muaj_2}</td>
                    <td style="padding: 12px 15px; text-align: center;">{mes_dite_l2l_m2:,.0f} kg/ditë</td>
                    <td style="padding: 12px 15px; text-align: center; font-weight: bold; color: #111;">{mes_dite_plote_m2:,.0f} kg/ditë</td>
                </tr>
                <tr style="border-bottom: none;">
                    <td style="padding: 12px 15px; font-weight: bold;">{emri_muaj_3}</td>
                    <td style="padding: 12px 15px; text-align: center;">{mes_dite_l2l_m3:,.0f} kg/ditë</td>
                    <td style="padding: 12px 15px; text-align: center; font-weight: bold; color: #111;">{mes_dite_plote_m3:,.0f} kg/ditë</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(html_tabela_mesatareve, unsafe_allow_html=True)
        st.write("")

        st.divider()

        # --- NDËRTIMI I GRAFIKUT FINAL ---
        fig = go.Figure()
        gjeresia_kolones = 0.6

        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_para_vit[:ditet_totale_m1],
                base=base_para_vit[:ditet_totale_m1],
                name=emri_muaj_3,
                width=gjeresia_kolones,
                marker_color="rgba(141, 211, 199, 0.55)",
                textposition="none",
                hovertemplate="%{y:,.0f} kg<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_para_muaj[:ditet_totale_m1],
                base=base_para_muaj[:ditet_totale_m1],
                name=emri_muaj_2,
                width=gjeresia_kolones,
                marker_color="rgba(0, 105, 92, 0.55)",
                textposition="none",
                hovertemplate="%{y:,.0f} kg<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_aktual,
                base=base_aktual,
                name=emri_muaj_1,
                width=gjeresia_kolones,
                marker_color="rgba(255, 193, 7, 0.65)",
                text=[f"{v:,.0f}" if v > 0 else "" for v in y_aktual],
                textposition="outside",
                hovertemplate="%{y:,.0f} kg<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"KASKADA KRAHASUESE E SHITJEVE DITORE ({emri_muaj_1})",
            barmode="overlay",
            plot_bgcolor="#eef2f3",
            height=650,
            xaxis=dict(
                title=f"Ditët e muajit ({muajt_sq.get(sel_muaj_1)})",
                tickangle=0,
                type="linear",
                tickmode="array",
                tickvals=ditet_numerik,
                ticktext=ditet_etiketa,
                range=[0.4, ditet_totale_m1 + 0.6],
            ),
            yaxis=dict(title="Shitjet (kg)", gridcolor="#ffffff"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

        # --- TABELA E DETAJUAR ORIGJINALE E SHITJEVE DITORE ---
        st.markdown(
            "<h4 style='color: #2c3e50; font-size:18px; margin-top:20px;'>📋 Tabela Krahasuese e të Dhënave Ditore</h4>",
            unsafe_allow_html=True,
        )

        tabela_df = pd.DataFrame(
            {
                "Dita": ditet_etiketa,
                f"{emri_muaj_1} (kg)": y_aktual,
                f"{emri_muaj_2} (kg)": [
                    data_para_muaj.get(d, {}).get(kolona_kg, 0.0) for d in ditet_numerik
                ],
                f"{emri_muaj_3} (kg)": [
                    data_para_vit.get(d, {}).get(kolona_kg, 0.0) for d in ditet_numerik
                ],
            }
        )

        st.dataframe(
            tabela_df.style.format(
                {
                    f"{emri_muaj_1} (kg)": "{:,.0f}",
                    f"{emri_muaj_2} (kg)": "{:,.0f}",
                    f"{emri_muaj_3} (kg)": "{:,.0f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.error("Të dhënat nuk u ngarkuan dot.")

# ---------------------------------------------------------
# MODULI I PLANIFIKIMIT STRUKTURAL (VETËM ARTIKUJT E SHITUR NË B)
# ---------------------------------------------------------


# 1. HAPI I PARË: Deklarojmë funksionin në mënyrë që Python ta njohë
def shfaq_modul_planifikimi_artikujve(df_baze_sales):
    st.title("🎯 Planifikimi i Artikujve sipas Strukturës së re (Periudha A ➔ B)")
    st.markdown(
        "Konverton shitjet mesatare të kategorive nga **Periudha A** në artikuj specifikë bazuar **VETËM** në mix-in e ri të shitjeve nga **Periudha B**."
    )
    df_proc = df_baze_sales.copy()
    df_proc["KodiArt"] = df_proc["KodiArt"].astype(str).str.strip()
    df_proc["KodiKlient"] = df_proc["KodiKlient"].astype(str).str.strip()
    df_proc["ForcaShitese"] = (
        df_proc["ForcaShitese"].fillna("Pa Agjent").astype(str).str.strip()
    )
    df_proc["kat"] = df_proc["kat"].fillna("Pa Kategori")
    df_proc["VitiMuaji"] = df_proc["Data"].dt.to_period("M")

    min_d = df_proc["Data"].min().date() if not df_proc.empty else datetime.now().date()
    max_d = df_proc["Data"].max().date() if not df_proc.empty else datetime.now().date()

    # --- LIBRARIA E RUAJTJES PËR MODULIN E RI ---
    if "libraria_modulit_ri" not in st.session_state:
        st.session_state["libraria_modulit_ri"] = {
            "Zgjedhje Manuale (Pa Ruajtje)": None
        }

    lib_ri = st.session_state["libraria_modulit_ri"]

    # --- KONTROLLI I NGARKIMIT TË PLANIT TË RUAJTUR ---
    with st.expander(
        "💾 Thirr ose Ruaj një Konfigurim të Planit (Periudha A, B dhe % Rritje)"
    ):
        c_l1, c_l2 = st.columns([2, 1])
        with c_l1:
            zgjedhje_plani = st.selectbox(
                "Thirr konfigurim të ruajtur më parë:",
                options=list(lib_ri.keys()),
                key="sel_lib_ri_key",
            )

        if (
            zgjedhje_plani != "Zgjedhje Manuale (Pa Ruajtje)"
            and lib_ri[zgjedhje_plani] is not None
        ):
            konfig = lib_ri[zgjedhje_plani]
            st.session_state["p_a_start"] = konfig["a_start"]
            st.session_state["p_a_end"] = konfig["a_end"]
            st.session_state["p_b_start"] = konfig["b_start"]
            st.session_state["p_b_end"] = konfig["b_end"]
            st.session_state["rritja_modul_ri"] = konfig["rritja"]

        st.divider()
        st.markdown("**Ruaj Konfigurimin Aktual:**")
        txt_emri_ri = st.text_input(
            "Vendos një emër për këtë konfigurim (psh: Plani Sezonit Vjeshtë):",
            key="emri_konfig_ri",
        )

        if st.button("➕ Ruaj Konfigurimin", use_container_width=True):
            if txt_emri_ri.strip() != "":
                lib_ri[txt_emri_ri] = {
                    "a_start": st.session_state.get("pl_range_a", (min_d, max_d))[0],
                    "a_end": st.session_state.get("pl_range_a", (min_d, max_d))[1],
                    "b_start": st.session_state.get("pl_range_b", (min_d, max_d))[0],
                    "b_end": st.session_state.get("pl_range_b", (min_d, max_d))[1],
                    "rritja": st.session_state.get("rritja_modul_ri", 0.0),
                }
                st.success(f"✅ Konfigurimi '{txt_emri_ri}' u ruajt me sukses!")
                st.rerun()
            else:
                st.error("Ju lutem vendosni një emër përpara se ta ruani.")

    # Inicializimi i vlerave nëse nuk ekzistojnë në session_state
    if "p_a_start" not in st.session_state:
        st.session_state["p_a_start"] = min_d
    if "p_a_end" not in st.session_state:
        st.session_state["p_a_end"] = max_d
    if "p_b_start" not in st.session_state:
        st.session_state["p_b_start"] = min_d
    if "p_b_end" not in st.session_state:
        st.session_state["p_b_end"] = max_d
    if "rritja_modul_ri" not in st.session_state:
        st.session_state["rritja_modul_ri"] = 0.0

    # --- INPUTET E PERIUDHAVE DHE % SË RRITJES ---
    st.subheader("⚙️ Parametrat e Gjenerimit")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("##### 📅 Periudha A (Kapaciteti)")
        p_a = st.date_input(
            "Rreza e datave për Periudhën A:",
            value=(st.session_state["p_a_start"], st.session_state["p_a_end"]),
            min_value=min_d,
            max_value=max_d,
            key="pl_range_a",
        )
    with col_b:
        st.markdown("##### 📅 Periudha B (Mix-i i Ri)")
        p_b = st.date_input(
            "Rreza e datave për Periudhën B:",
            value=(st.session_state["p_b_start"], st.session_state["p_b_end"]),
            min_value=min_d,
            max_value=max_d,
            key="pl_range_b",
        )
    with col_c:
        st.markdown("##### 📈 % e Rritjes së Planit")
        rritja_p = st.number_input(
            "Vendos përqindjen e rritjes target:",
            value=st.session_state["rritja_modul_ri"],
            step=1.0,
            key="rritja_modul_ri",
        )

    # --- FILTRIMI SIPAS AGJENTËVE ---
    st.subheader("👤 Filtrimi i Agjentëve")
    lista_agjenteve = sorted(df_proc["ForcaShitese"].unique())
    agjentet_zgjedhur = st.multiselect(
        "Zgjidh agjentët që dëshiron të përfshish në plan (Lëre bosh për të gjithë):",
        options=lista_agjenteve,
    )

    if (
        isinstance(p_a, tuple)
        and len(p_a) == 2
        and isinstance(p_b, tuple)
        and len(p_b) == 2
    ):
        if st.button(
            "🚀 Gjenero Planin Struktural të Avancuar", use_container_width=True
        ):

            if agjentet_zgjedhur:
                df_proc = df_proc[df_proc["ForcaShitese"].isin(agjentet_zgjedhur)]

            df_A = df_proc[
                (df_proc["Data"] >= pd.to_datetime(p_a[0]))
                & (df_proc["Data"] <= pd.to_datetime(p_a[1]))
            ]
            df_B = df_proc[
                (df_proc["Data"] >= pd.to_datetime(p_b[0]))
                & (df_proc["Data"] <= pd.to_datetime(p_b[1]))
            ]

            if df_A.empty or df_B.empty:
                st.warning(
                    "⚠️ Nuk u gjetën shitje në njërën prej periudhave të përzgjedhura. Ndryshoni datat."
                )
                return

            # FAZA 1: Mesatarja e Klientit dhe Agjentit për Kategori në Periudhën A
            muaj_unike_A = df_A["VitiMuaji"].nunique()
            nr_muajve_A = muaj_unike_A if muaj_unike_A > 0 else 1

            df_klient_A = (
                df_A.groupby(["ForcaShitese", "KodiKlient", "Klienti", "kat"])["kg"]
                .sum()
                .reset_index()
            )
            df_klient_A["Mesatare_KG_Kategori"] = df_klient_A["kg"] / nr_muajve_A
            df_klient_A = df_klient_A.drop(columns=["kg"])

            # FAZA 2: Mix-i i shitjeve të artikujve në Periudhën B brenda kategorisë
            tot_kat_B = (
                df_B.groupby("kat")["kg"]
                .sum()
                .reset_index()
                .rename(columns={"kg": "Tot_Kat_B"})
            )
            tot_art_B = (
                df_B.groupby(["kat", "KodiArt", "Artikulli"])["kg"]
                .sum()
                .reset_index()
                .rename(columns={"kg": "Tot_Art_B"})
            )

            df_mix_B = pd.merge(tot_art_B, tot_kat_B, on="kat")
            df_mix_B["Pesha_Artikullit"] = np.where(
                df_mix_B["Tot_Kat_B"] > 0,
                df_mix_B["Tot_Art_B"] / df_mix_B["Tot_Kat_B"],
                0,
            )
            df_mix_B = df_mix_B[["kat", "KodiArt", "Artikulli", "Pesha_Artikullit"]]

            # 🔥 FILTRI KRITIK: Mbajmë VETËM artikujt që kanë pasur shitje reale (peshë > 0) në Periudhën B
            df_mix_B = df_mix_B[df_mix_B["Pesha_Artikullit"] > 0]

            # FAZA 3: Kombinimi Matematik i Planit (inner join siguron që mbeten vetëm artikujt e filtruar mësipër)
            df_plani = pd.merge(df_klient_A, df_mix_B, on="kat", how="inner")

            faktor_rritje = 1 + (rritja_p / 100.0)
            df_plani["Plani_KG"] = (
                df_plani["Mesatare_KG_Kategori"]
                * df_plani["Pesha_Artikullit"]
                * faktor_rritje
            )

            # Konvertimi në Copa sipas peshës nominale
            try:
                df_peshat = df_proc[["KodiArt", "KG/SKU"]].drop_duplicates()
                df_plani = pd.merge(df_plani, df_peshat, on="KodiArt", how="left")
                df_plani["Plani_Cope"] = np.where(
                    df_plani["KG/SKU"] > 0, df_plani["Plani_KG"] / df_plani["KG/SKU"], 0
                )
            except Exception:
                df_plani["Plani_Cope"] = 0

            # --- KRIJIMI I TABELAVE TË NDARA (KATEGORI DHE ARTIKUJ) ---
            df_agj_kategori = (
                df_plani.groupby(["ForcaShitese", "kat"])[["Plani_KG", "Plani_Cope"]]
                .sum()
                .reset_index()
            )
            df_agj_kategori.columns = [
                "Agjenti",
                "Kategoria",
                "Plani Target (KG)",
                "Plani Target (Copa)",
            ]

            df_agj_artikuj = (
                df_plani.groupby(["ForcaShitese", "kat", "KodiArt", "Artikulli"])[
                    ["Plani_KG", "Plani_Cope"]
                ]
                .sum()
                .reset_index()
            )
            df_agj_artikuj.columns = [
                "Agjenti",
                "Kategoria",
                "Kodi Art.",
                "Artikulli",
                "Plani Target (KG)",
                "Plani Target (Copa)",
            ]

            st.success(
                f"✅ Plani i ri struktural u kalkulua me sukses! Përfshihen vetëm artikujt aktivë të shitur në Periudhën B me +{rritja_p}% rritje."
            )

            # --- SHFAQJA NË TABS ---
            tab1, tab2 = st.tabs(
                ["📊 Përmbledhja sipas Kategorive", "📦 Detajet sipas Artikujve"]
            )

            with tab1:
                st.dataframe(df_agj_kategori, use_container_width=True)
            with tab2:
                st.dataframe(df_agj_artikuj, use_container_width=True)

            # --- EKSPORTI NË EXCEL (Multi-Sheet) ---
            import io

            out_xl = io.BytesIO()
            with pd.ExcelWriter(out_xl, engine="xlsxwriter") as wr:
                df_agj_kategori.to_excel(
                    wr, index=False, sheet_name="Plani_sipas_Kategorive"
                )
                df_agj_artikuj.to_excel(
                    wr, index=False, sheet_name="Plani_sipas_Artikujve"
                )

            st.download_button(
                label="📥 Shkarko të dyja tabelat në Excel",
                data=out_xl.getvalue(),
                file_name="plani_struktural_agjente.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

            # --- GJENERIMI I RAPORTIT PDF ---
            st.subheader("📄 Gjenerimi i Raportit PDF")

            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; margin: 20px; }}
                    h1 {{ text-align: center; color: #1f4e78; font-size: 24px; }}
                    h2 {{ color: #2e74b5; border-bottom: 2px solid #2e74b5; padding-bottom: 5px; font-size: 16px; margin-top: 30px; }}
                    .meta-box {{ background-color: #f2f2f2; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-size: 12px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
                    th {{ background-color: #1f4e78; color: white; padding: 6px; text-align: left; border: 1px solid #ddd; }}
                    td {{ padding: 5px; border: 1px solid #ddd; text-align: left; }}
                    .num {{ text-align: right; }}
                    .footer {{ text-align: center; font-size: 10px; color: #7f7f7f; margin-top: 40px; }}
                </style>
            </head>
            <body>
                <h1>RAPORTI I PLANIFIKIMIT STRUKTURAL STRATEGJIK</h1>
                <div class="meta-box">
                    <strong>Konfigurimi i Sistemit:</strong><br>
                    • Periudha A (Kapaciteti): {p_a[0].strftime('%d/%m/%Y')} - {p_a[1].strftime('%d/%m/%Y')}<br>
                    • Periudha B (Filtri i Mix-it të Ri): {p_b[0].strftime('%d/%m/%Y')} - {p_b[1].strftime('%d/%m/%Y')}<br>
                    • Rritja e Aplikuar Target: <strong>+{rritja_p}%</strong><br>
                    • Shënim Logjik: Përfshihen vetëm artikujt me performancë aktive në Periudhën B.<br>
                    • Data e Gjenerimit: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                </div>

                <h2>1. Përmbledhja e Planeve sipas Agjentëve dhe Kategorive</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Agjenti</th>
                            <th>Kategoria</th>
                            <th class="num">Plani Target (KG)</th>
                            <th class="num">Plani Target (Copa)</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for _, row in df_agj_kategori.head(200).iterrows():
                html_content += f"""
                        <tr>
                            <td>{row['Agjenti']}</td>
                            <td>{row['Kategoria']}</td>
                            <td class="num">{row['Plani Target (KG)']:,.1f}</td>
                            <td class="num">{row['Plani Target (Copa)']:,.0f}</td>
                        </tr>
                """

            html_content += """
                    </tbody>
                </table>
                <div class="footer">Sistemi i Menaxhimit të Planifikimit © AXION - DEKA SQL</div>
            </body>
            </html>
            """

            import io

            try:
                from weasyprint import HTML

                pdf_out = io.BytesIO()
                HTML(string=html_content).write_pdf(pdf_out)

                st.download_button(
                    label="📕 Shkarko Raportin Ekzekutiv në format PDF",
                    data=pdf_out.getvalue(),
                    file_name="raporti_plani_struktural.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.info(
                    "💡 Për të shkarkuar versionin PDF direkt në Streamlit Cloud, sigurohuni që keni shtuar 'weasyprint' te requirements.txt. Ndërkohë, skedari i plotë i detajuar Excel i mësipërm është gati për përdorim."
                )
    else:
        st.info(
            "💡 Ju lutem përzgjedhni rrezen e plotë të datave për të dyja periudhat që të aktivizohet butoni i kalkulimit."
        )


# 2. HAPI I DYTË: Kushti "if" vendoset VETËM pasi funksioni është krijuar plotësisht më lart!
if page == "🎯 Plani sipas Strukturës B":
    shfaq_modul_planifikimi_artikujve(df_raw)
    st.stop()  # Ndalon përplasjen me modulin e vjetër poshtë

# endregion

# =========================================================
# MODULI: AI DATA ASSISTANT (VERSIONI TEKNIK I PASTRUAR)
# region ==================================================
import anthropic
import streamlit as st
import pandas as pd


def shfaq_ai_assistant(df):
    st.subheader("🤖 AXION AI – Asistenti Inteligjent i Planeve dhe Analizave")
    st.markdown(
        "Bisedo me AI për të ndërtuar plane biznesi. AI i llogarit shifrat vetë dhe mban mend bisedën."
    )

    # 1. Konfigurimi i API Key
    api_key = st.secrets.get("CLAUDE_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input(
            "Vendos Anthropic API Key (sk-ant-...):", type="password"
        )
        if not api_key:
            st.info(
                "🔑 Ju lutem vendosni API Key-n tuaj të Anthropic në sidebar për të aktivizuar Asistentin AI."
            )
            st.stop()

    try:
        client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        st.error(f"Gabim gjate konfigurimit te Anthropic: {e}")
        st.stop()

    # Informojme AI-n per strukturen ekzakte te te dhenave tuaja
    emrat_kolonave = ", ".join(df.columns.tolist())

    system_instruction = f"""
    Ti je AXION AI, ekspert ne analizen e shitjeve ERP. Perdoruesi deshiren plane komplekse si ai i Qershorit 2026.
    Ne shembullin e tij te fundit, rezultati doli 30 here me i larte sepse u be nje Cross-Join i gabuar midis muajve dhe artikujve. 
    Duhet te jesh shume i kujdesshem me matematiken dhe agregimet.
    
    Nese te duhet te besh llogaritje mbi tabelen (e cila quhet 'df'), ti duhet te shkruash nje kod Python qe filtron dhe agregon te dhenat sakte.
    
    Kolonat e tabeles 'df' jane: {emrat_kolonave}
    - Data (format datetime)
    - ForcaShitese (agjentet)
    - Klienti / KodiKlient
    - kat (Kategorite e produkteve)
    - Sasia (Sasia e shitur)
    - kg (Sasia ne kilograme)
    - Vlera_Historike (Vlera ne Leke)
    - Grup_Filtri (DEKA, OLIM, ETJ)

    RREGULLI I PERGJIGJES:
    Pergjigju ne gjuhen shqipe duke i shpjeguar logjiken perdoruesit. Nese ke llogaritur nje tabele, shfaqe kodin e llogaritjes brenda bllokut standard:
```python
    # Kodi duhet te krijoje GJITHMONE nje variabel te quajtur 'rezultati_final'
    df_filtered = df[df['Grup_Filtri'] == 'DEKA']
    rezultati_final = df_filtered.groupby('Artikulli').agg(Vlera=('Vlera_Historike', 'sum')).reset_index()
    ```
    Mos harro: variabla finale e rezultatit duhet te quhet ekzaktesisht 'rezultati_final' qe aplikacioni ta shfaqe ne ekran.
    """

    # Inicializimi i historikut te bisedes
    if "messages_chat" not in st.session_state:
        st.session_state.messages_chat = [
            {
                "role": "assistant",
                "content": "Pershendetje! Jam AXION AI. Jam gati te rregullojme planin e Qershorit 2026 hap pas hapi qe te mos kemi rritje artificiale shifrash. Cfare deshironi te llogarisim si fillim?",
            }
        ]

    # Shfaq biseden e deritanishme
    for msg in st.session_state.messages_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Kutia e Chat-it ne fund te faqes
    if prompt := st.chat_input("Shkruaj kerkesen tuaj ketu..."):
        st.session_state.messages_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Duke analizuar dhe llogaritur..."):
                try:
                    # Pergatitja e historikut per Claude
                    api_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages_chat
                    ]

                    # Ndryshojme pak instruksionin lokal qe Claude te na jape edhe tekst edhe kod
                    instruksioni_ri = (
                        system_instruction
                        + "\nKujdes: Shpjegoni rezultatin ne gjuhen shqipe normalisht. Por kodin Python futeni VETEM brenda tagit [KODI] dhe [/KODI]."
                    )

                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=1500,
                        system=instruksioni_ri,
                        messages=api_messages,
                    )

                    pergjigje_ai = response.content[0].text

                    # 1. Pastrojme tekstin nga tagu i kodit qe t'i shfaqet perdoruesit vetem shpjegimi njerëzor
                    tekst_per_shfaqje = pergjigje_ai
                    if "[KODI]" in tekst_per_shfaqje:
                        tekst_per_shfaqje = (
                            tekst_per_shfaqje.split("[KODI]")[0]
                            + "\n*(Tabela u llogarit me sukses me poshte)*"
                        )

                    st.write(tekst_per_shfaqje)

                    # Ruajme mesazhin ne historik
                    st.session_state.messages_chat.append(
                        {"role": "assistant", "content": pergjigje_ai}
                    )

                    # 2. Izolojme dhe ekzekutojme kodin Python ne prapaskene
                    if "[KODI]" in pergjigje_ai:
                        pjesa_kodit = (
                            pergjigje_ai.split("[KODI]")[1].split("[/KODI]")[0].strip()
                        )

                        # Pastrim nese ka mbetur ndonje shenje markdown-i ```python
                        if "```python" in pjesa_kodit:
                            pjesa_kodit = (
                                pjesa_kodit.split("```python")[1]
                                .split("```")[0]
                                .strip()
                            )
                        elif "```" in pjesa_kodit:
                            pjesa_kodit = pjesa_kodit.split("```")[1].strip()

                        # Executojme kodin e gjeneruar
                        lokalet = {"df": df, "pd": pd}
                        exec(pjesa_kodit, globals(), lokalet)

                        # Nese kodi krijoi 'rezultati_final', e shfaqim si tabele interaktive
                        if "rezultati_final" in lokalet:
                            st.success("📊 Tabela e llogaritur nga AI:")
                            st.dataframe(
                                lokalet["rezultati_final"], use_container_width=True
                            )

                            # Butoni per shkarkim ne Excel
                            st.download_button(
                                label="📥 Shkarko kete tabele ne Excel",
                                data=lokalet["rezultati_final"]
                                .to_csv(index=False)
                                .encode("utf-8"),
                                file_name="analiza_axion_ai.csv",
                                mime="text/csv",
                            )
                except Exception as e:
                    st.error(f"⚠️ Ndodhi nje gabim brenda bisedes: {e}")


# KOD INTEGRIMI I SIGURUAR (Nuk varet nga variabla 'page' nese ajo ka gabim)
try:
    if page == "AI Assistant":
        if "df_raw" in locals() or "df_raw" in globals():
            if df_raw is not None:
                shfaq_ai_assistant(df_raw)
            else:
                st.error("❌ Nuk u gjeten te dhena valide nga SQL Server.")
        else:
            st.warning("⚠️ Prisni ngarkimin e te dhenave...")
        st.stop()
except NameError:
    # Nese variabla 'page' nuk ekziston ne kodin tend, kjo parandalon faqen e bardhe
    pass

# endregion
