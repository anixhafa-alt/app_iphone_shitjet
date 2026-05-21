import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os
import numpy as np
import time

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
    if st.session_state["password"] == "a":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
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
        "Planifikimi",  # Ky mbetet moduli yt ekzistues (grafikët, etj.)
        "🎯 Plani sipas Strukturës B",  # Moduli i ri inteligjent
        "Mundësitë",
        "Historiku",
        "Klientët me shumë Agjentë",
        "Asistenti AI",
        "Route Plan AI",
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
            "SELECT Data, ForcaShitese, KodiKlient, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView"
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
# MODULI: HISTORIKU
# ---------------------------------------------------------
if page == "Historiku":
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
        chart_data = df_final.groupby(["Viti", "Muaji"])["kg"].sum().reset_index()
        if not chart_data.empty:
            chart_pivot = chart_data.pivot(
                index="Muaji", columns="Viti", values="kg"
            ).fillna(0)
            chart_pivot.index = [muajt_sq.get(m, m) for m in chart_pivot.index]
            st.line_chart(chart_pivot)

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
        csv = tabela_artikujt.to_csv().encode("utf-8")
        st.download_button(
            label="📥 Shkarko Listën e Plotë (CSV)",
            data=csv,
            file_name="historiku_artikujve.csv",
            mime="text/csv",
        )

# ---------------------------------------------------------
# MODULI: PLANIFIKIMI
# ---------------------------------------------------------
elif page == "Planifikimi" and df_raw is not None:

    sot = datetime.now()

    data_fundit_db = df_raw["Data"].max().strftime("%d/%m/%Y")

    # --- LOGJIKA E ÇMIMIT TË FUNDIT (Përjashton muajin korrent) ---

    # Marrim vetëm të dhënat që nuk i përkasin muajit dhe vitit aktual

    mask_past = (df_raw["Data"].dt.year < sot.year) | (
        (df_raw["Data"].dt.year == sot.year) & (df_raw["Data"].dt.month < sot.month)
    )

    df_past = df_raw[mask_past].copy()

    df_past["Cmimi_Rresht"] = df_past["Vlera_Historike"] / df_past["kg"].replace(0, 1)

    last_prices = df_past.sort_values("Data").drop_duplicates("KodiArt", keep="last")[
        ["KodiArt", "Cmimi_Rresht"]
    ]

    last_prices.rename(columns={"Cmimi_Rresht": "Cmimi_Fundit_Artikulli"}, inplace=True)

    # --- FILTRIMI ---

    mask = (df_raw["Data"].dt.date >= start_date) & (df_raw["Data"].dt.date <= end_date)

    dff = df_raw.loc[mask].copy()

    if grup_sel != "Të gjitha":
        dff = dff[dff["Grup_Filtri"] == grup_sel]

    if agj_sel != "Të gjithë":
        dff = dff[dff["ForcaShitese"] == agj_sel]

    if klientet_selected:
        dff = dff[dff["Klienti"].isin(klientet_selected)]

    n_months = max(
        1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    )

    # Ruajmë vlerat në session_state që t'i përdorim te Realizimi

    st.session_state["start_d_plani"] = start_date

    st.session_state["end_d_plani"] = end_date

    st.session_state["rritja_plani"] = rritja

    st.session_state["grup_plani"] = grup_sel

    # --- AGREGIMI ---

    gp = (
        dff.groupby(["ForcaShitese", "Klienti", "kat", "KodiArt", "Artikulli"])
        .agg({"kg": "sum", "Vlera_Historike": "sum"})
        .reset_index()
    )
    # INTEGRIMI DHE SAKTËSIMI I PLANIT:
    if df_klientet_regjistri is not None:
        # Pasi në tabelën historike mund të keni emrin e klientit ndryshe, bashkimin e bëjmë me Kodin e Klientit
        # Nëse df_raw-i yt nuk ka kolonë 'KodiKlient', duhet të sigurohesh që kodi i klientit të jetë i pranishëm në dff.
        # Supozojmë që bëhet bashkimi për të marrë të dhënat aktuale:

        # Filtrojmë vetëm klientët aktivë [V] për të saktësuar rrugët e planit
        df_aktive = df_klientet_regjistri[df_klientet_regjistri["StatusiAktiv"] == True]

        # Mund të zëvendësosh ForcaShitese me ForcaShiteseAktuale për të ri-alokuar volumet automatikisht.
    gp["Cmimi_Mes_Periudhes"] = gp["Vlera_Historike"] / gp["kg"].replace(0, 1)

    gp = gp.merge(last_prices, on="KodiArt", how="left")

    gp["Plani_KG"] = (gp["kg"] / n_months) * (1 + rritja / 100)

    gp["Vlera_Planifikuar"] = gp["Plani_KG"] * gp["Cmimi_Fundit_Artikulli"].fillna(
        gp["Cmimi_Mes_Periudhes"]
    )

    # --- TITULLI DHE METRICS (Titulli tashmë është muaji korrent) ---
    # st.title(f"🎯 Plani: {muajt_sq.get(sot.month)} {sot.year}")
    st.title(f"Plani: {muajt_sq.get(sot.month)} {sot.year}")

    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    st.info(f"Update i fundit: **{data_fundit_db}** | Grupi: **{grup_sel}**")

    t_kg_ref = gp["kg"].sum()

    t_v_ref = gp["Vlera_Historike"].sum()

    cm_mes_ref = t_v_ref / t_kg_ref if t_kg_ref > 0 else 0

    t_kg_plan = gp["Plani_KG"].sum()

    t_v_plan = gp["Vlera_Planifikuar"].sum()

    cm_mes_plan = t_v_plan / t_kg_plan if t_kg_plan > 0 else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Plani KG Totale", f"{t_kg_plan:,.0f}")

    c2.metric("Çmimi Mes. Periudhës", f"{cm_mes_ref:,.1f} L/kg")

    c3.metric(
        "Çmimi Fundit Mes.",
        f"{cm_mes_plan:,.1f} L/kg",
        delta=f"{cm_mes_plan - cm_mes_ref:,.1f} L",
    )

    c4.metric("Vlera Totale Plani", f"{t_v_plan:,.0f} L")

    config_kolonave = {
        "Cmimi_Mes_Periudhes": st.column_config.NumberColumn(
            "Çmimi Mes. Periudhës", format="%.1f L"
        ),
        "Cmimi_Fundit_Artikulli": st.column_config.NumberColumn(
            "Çmimi i Fundit", format="%.1f L"
        ),
        "Cmimi_Mes_Grup": st.column_config.NumberColumn(
            "Çmimi (Fundit) Mes.", format="%.1f L"
        ),
        "Plani_KG": st.column_config.NumberColumn("Plani KG", format="%d"),
        "Vlera_Planifikuar": st.column_config.NumberColumn("Vlera Planit", format="%d"),
    }

    st.divider()

    # --- TABET ---

    if klientet_selected:

        st.subheader("📍 Detajet Artikujve")

        st.dataframe(
            gp[
                [
                    "Klienti",
                    "kat",
                    "Artikulli",
                    "Cmimi_Mes_Periudhes",
                    "Cmimi_Fundit_Artikulli",
                    "Plani_KG",
                    "Vlera_Planifikuar",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config=config_kolonave,
        )

    else:

        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])

        with t1:

            df_k = (
                gp.groupby("kat")
                .agg(
                    {
                        "Plani_KG": "sum",
                        "Vlera_Planifikuar": "sum",
                        "kg": "sum",
                        "Vlera_Historike": "sum",
                    }
                )
                .reset_index()
            )

            df_k["Cmimi_Mes_Periudhes"] = df_k["Vlera_Historike"] / df_k["kg"].replace(
                0, 1
            )

            df_k["Cmimi_Mes_Grup"] = df_k["Vlera_Planifikuar"] / df_k[
                "Plani_KG"
            ].replace(0, 1)

            st.dataframe(
                df_k[
                    [
                        "kat",
                        "Cmimi_Mes_Periudhes",
                        "Cmimi_Mes_Grup",
                        "Plani_KG",
                        "Vlera_Planifikuar",
                    ]
                ].sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
                column_config=config_kolonave,
            )

        with t2:

            df_a = (
                gp.groupby("ForcaShitese")
                .agg(
                    {
                        "Plani_KG": "sum",
                        "Vlera_Planifikuar": "sum",
                        "kg": "sum",
                        "Vlera_Historike": "sum",
                    }
                )
                .reset_index()
            )

            df_a["Cmimi_Mes_Periudhes"] = df_a["Vlera_Historike"] / df_a["kg"].replace(
                0, 1
            )

            df_a["Cmimi_Mes_Grup"] = df_a["Vlera_Planifikuar"] / df_a[
                "Plani_KG"
            ].replace(0, 1)

            st.dataframe(
                df_a[
                    [
                        "ForcaShitese",
                        "Cmimi_Mes_Periudhes",
                        "Cmimi_Mes_Grup",
                        "Plani_KG",
                        "Vlera_Planifikuar",
                    ]
                ].sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
                column_config=config_kolonave,
            )

        with t3:

            df_kl = (
                gp.groupby(["Klienti", "ForcaShitese"])
                .agg(
                    {
                        "Plani_KG": "sum",
                        "Vlera_Planifikuar": "sum",
                        "kg": "sum",
                        "Vlera_Historike": "sum",
                    }
                )
                .reset_index()
            )

            df_kl["Cmimi_Mes_Periudhes"] = df_kl["Vlera_Historike"] / df_kl[
                "kg"
            ].replace(0, 1)

            df_kl["Cmimi_Mes_Grup"] = df_kl["Vlera_Planifikuar"] / df_kl[
                "Plani_KG"
            ].replace(0, 1)

            st.dataframe(
                df_kl[
                    [
                        "Klienti",
                        "ForcaShitese",
                        "Cmimi_Mes_Periudhes",
                        "Cmimi_Mes_Grup",
                        "Plani_KG",
                        "Vlera_Planifikuar",
                    ]
                ].sort_values("Plani_KG", ascending=False),
                width="stretch",
                hide_index=True,
                column_config=config_kolonave,
            )

    # --- EKSPORTI ---

    def generate_html_report(dataframe):

        html = "<html><head><style>body{font-family:sans-serif;} table{width:100%; border-collapse:collapse;} th,td{border:1px solid #ddd; padding:8px; text-align:left;} th{background-color:#f2f2f2;} .num{text-align:right;}</style></head><body>"

        html += f"<h1>Raporti i Planit ({grup_sel})</h1>"

        for agjent in sorted(dataframe["ForcaShitese"].unique()):

            html += f"<h3>Agjenti: {agjent}</h3>"

            agj_df = (
                dataframe[dataframe["ForcaShitese"] == agjent]
                .groupby("kat")
                .agg({"Plani_KG": "sum", "Vlera_Planifikuar": "sum"})
                .reset_index()
            )

            html += "<table><thead><tr><th>Kategoria</th><th class='num'>Plani (KG)</th><th class='num'>Vlera</th></tr></thead><tbody>"

            for _, row in agj_df.iterrows():

                html += f"<tr><td>{row['kat']}</td><td class='num'>{row['Plani_KG']:,.0f}</td><td class='num'>{row['Vlera_Planifikuar']:,.0f} L</td></tr>"

            html += "</tbody></table><br>"

        html += "</body></html>"

        return html

    if st.sidebar.button("Gjenero Raportin HTML"):

        b64 = base64.b64encode(generate_html_report(gp).encode()).decode()

        st.sidebar.markdown(
            f'<a href="data:text/html;base64,{b64}" download="Plani.html" style="padding:10px; background-color:#2e75b6; color:white; text-decoration:none; border-radius:5px;">Shkarko Raportin</a>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------
# MODULI: REALIZIMI
# ---------------------------------------------------------
elif page == "Realizimi":
    import numpy as np

    sot = datetime.now()
    # st.title(f"📈 Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")
    st.title(f"Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

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

        gp_target_cat = dff_ref.groupby(["kat"]).agg({"kg": "sum"}).reset_index()
        gp_target_cat["KG_Target"] = (
            gp_target_cat["kg"] / n_months_ref
        ) * rritja_faktori
        t_target = gp_target_cat["KG_Target"].sum()

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

        # --- LLOGARITJA E ÇMIMIT MESATAR LIVE (KORRIGJUAR) ---
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

        # --- 3. METRIKAT KRYESORE ---
        total_perc = (t_real / t_target * 100) if t_target > 0 else 0
        c1, c2, c5, c3, c4 = st.columns(
            5
        )  # Ndryshuar në 5 kolona për të rreshtuar Çmimin Mesatar
        c1.metric("Target KG", f"{t_target:,.0f}")
        c2.metric("Realizuar KG", f"{t_real:,.0f}")
        status_color = "normal" if total_perc >= koha_perq else "inverse"
        c3.metric(
            "Realizimi %",
            f"{total_perc:.1f}%",
            delta=f"{total_perc - koha_perq:.1f}% vs Koha",
            delta_color=status_color,
        )
        c4.metric(
            "Ditë Pune",
            f"{ditet_punes_deri_sot}/{ditet_punes_totale}",
            f"{koha_perq:.1f}% e muajit",
        )
        c5.metric(
            "Çmimi Mes./kg", f"{cmimi_mesatar:,.1f} Lekë"
        )  # Shfaqja e metrikës së re

        st.divider()

        # --- 4. ANALIZA E TRENDËVE (Me Filtra Dinamikë) ---
        st.subheader("🔍 Analiza e Trendeve (Krahasim me të njëjtën periudhë)")
        tr1, tr2, tr3 = st.columns(3)

        # A. Trendi Linear
        ritmi_punes = t_real / ditet_punes_deri_sot if ditet_punes_deri_sot > 0 else 0
        projeksioni = ritmi_punes * ditet_punes_totale
        tr1.metric(
            "Trendi Linear",
            f"{projeksioni:,.0f} kg",
            delta=f"{projeksioni - t_target:,.0f} vs Plani",
        )

        # B. vs Muaji Kaluar (Prill deri në datën korrente)
        m_kaluar_date = sot - pd.DateOffset(months=1)
        mask_m = (
            (df_raw["Data"].dt.year == m_kaluar_date.year)
            & (df_raw["Data"].dt.month == m_kaluar_date.month)
            & (df_raw["Data"].dt.day <= sot.day)
        )

        df_m_kaluar = df_raw[mask_m].copy()

        # APLIKIMI I FILTRAVE (Kjo rregullon vlerat që nuk ndryshonin)
        if grup_sel != "Të gjitha":
            df_m_kaluar = df_m_kaluar[df_m_kaluar["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_m_kaluar = df_m_kaluar[df_m_kaluar["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_m_kaluar = df_m_kaluar[df_m_kaluar["Klienti"].isin(klientet_selected)]

        t_m_kaluar = df_m_kaluar["kg"].sum()
        rritja_m = ((t_real / t_m_kaluar) - 1) * 100 if t_m_kaluar > 0 else 0
        tr2.metric("vs Muaji Kaluar", f"{t_m_kaluar:,.0f} kg", delta=f"{rritja_m:.1f}%")

        # C. vs Viti Kaluar (Maj 2025 deri në datën korrente)
        v_kaluar_date = sot - pd.DateOffset(years=1)
        mask_v = (
            (df_raw["Data"].dt.year == v_kaluar_date.year)
            & (df_raw["Data"].dt.month == v_kaluar_date.month)
            & (df_raw["Data"].dt.day <= sot.day)
        )

        df_v_kaluar = df_raw[mask_v].copy()

        # APLIKIMI I FILTRAVE (Edhe për vitin e kaluar)
        if grup_sel != "Të gjitha":
            df_v_kaluar = df_v_kaluar[df_v_kaluar["Grup_Filtri"] == grup_sel]
        if agj_sel != "Të gjithë":
            df_v_kaluar = df_v_kaluar[df_v_kaluar["ForcaShitese"] == agj_sel]
        if klientet_selected:
            df_v_kaluar = df_v_kaluar[df_v_kaluar["Klienti"].isin(klientet_selected)]

        t_v_kaluar = df_v_kaluar["kg"].sum()
        rritja_v = ((t_real / t_v_kaluar) - 1) * 100 if t_v_kaluar > 0 else 0
        tr3.metric("vs Viti Kaluar", f"{t_v_kaluar:,.0f} kg", delta=f"{rritja_v:.1f}%")

        st.divider()

        # --- 5. TABET ME BARET E PROGRESIT (Barat e kuqe) ---
        st.divider()

        # --- TABET E REALIZIMIT ---
        df_comp = gp_target_cat.copy()
        df_comp = pd.merge(
            df_comp[["kat", "KG_Target"]],
            df_live.groupby("kat", as_index=False).agg(KG_Real=("kg", "sum")),
            on="kat",
            how="left",
        ).fillna(0)

        t1, t2, t3 = st.tabs(["📊 Kategoritë", "👤 Agjentët", "🏪 Klientët"])

        with t1:
            st.subheader("Ecuria sipas Kategorive")
            df_comp["Progresi"] = (
                df_comp["KG_Real"] / df_comp["KG_Target"] * 100
            ).clip(upper=100)
            st.dataframe(
                df_comp[["kat", "KG_Target", "KG_Real", "Progresi"]],
                column_config={
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
                },
                hide_index=True,
                use_container_width="stretch",
            )

        with t2:
            st.subheader("Ecuria sipas Agjentëve")
            # Agregimi live për agjentët
            gp_agj_target = (
                dff_ref.groupby("ForcaShitese").agg({"kg": "sum"}).reset_index()
            )
            gp_agj_target["Target_AGJ"] = (
                gp_agj_target["kg"] / n_months_ref
            ) * rritja_faktori

            gp_agj_live = (
                df_live.groupby("ForcaShitese")
                .agg({"kg": "sum"})
                .reset_index()
                .rename(columns={"kg": "Real_AGJ"})
            )

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
                    "Target_AGJ": st.column_config.NumberColumn("Target", format="%d"),
                    "Real_AGJ": st.column_config.NumberColumn("Realizuar", format="%d"),
                    "%": st.column_config.ProgressColumn(
                        "Ecuria", min_value=0, max_value=100, format="%.1f%%"
                    ),
                },
                hide_index=True,
                use_container_width="stretch",
            )

        with t3:
            st.subheader("Ecuria sipas Klientëve")
            # Agregimi live për klientët
            gp_kl_target = (
                dff_ref.groupby(["Klienti", "ForcaShitese"])
                .agg({"kg": "sum"})
                .reset_index()
            )
            gp_kl_target["Target_KL"] = (
                gp_kl_target["kg"] / n_months_ref
            ) * rritja_faktori

            gp_kl_live = (
                df_live.groupby("Klienti")
                .agg({"kg": "sum"})
                .reset_index()
                .rename(columns={"kg": "Real_KL"})
            )

            df_kl = pd.merge(
                gp_kl_target[["Klienti", "ForcaShitese", "Target_KL"]],
                gp_kl_live,
                on="Klienti",
                how="left",
            ).fillna(0)
            df_kl["%"] = (df_kl["Real_KL"] / df_kl["Target_KL"] * 100).clip(upper=100)

            # Shfaqim vetëm klientët që kanë një target (për të shmangur listat e pafundme)
            df_kl = df_kl[df_kl["Target_KL"] > 0]

            st.dataframe(
                df_kl.sort_values("%", ascending=False),
                column_config={
                    "Klienti": "Klienti",
                    "ForcaShitese": "Agjenti",
                    "Target_KL": st.column_config.NumberColumn("Target", format="%d"),
                    "Real_KL": st.column_config.NumberColumn("Realizuar", format="%d"),
                    "%": st.column_config.ProgressColumn(
                        "Ecuria", min_value=0, max_value=100, format="%.1f%%"
                    ),
                },
                hide_index=True,
                use_container_width="stretch",
            )

        # --- 7. EKSPORTI NË HTML (Me Filtra dhe Emër Dinamik) ---
        st.divider()

        # Përgatitja e emrit të fajlit
        agj_emri_fajl = (
            agj_sel.replace(" ", "_") if agj_sel != "Të gjithë" else "Gjithe_Agjentet"
        )
        file_name_custom = f"Raport_{agj_emri_fajl}_{sot.strftime('%d_%m_%Y')}.html"

        # Përgatitja e tekstit të klientëve për HTML
        klientet_text = (
            ", ".join(klientet_selected) if klientet_selected else "Të gjithë"
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
                .stats-container {{ display: flex; justify-content: space-between; margin: 20px 0; gap: 15px; }}
                .stat-box {{ background: white; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1a237e; width: 18%; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                .stat-box h3 {{ margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #777; }}
                .stat-box p {{ font-size: 22px; font-weight: bold; margin: 10px 0; color: #1a237e; }}
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
                <h1 style="margin:0;">Analiza e Realizimit: {muajt_sq.get(sot.month)} {sot.year}</h1>
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
                <div class="stat-box"><h3>Targeti (Muaj)</h3><p>{t_target:,.0f} kg</p></div>
                <div class="stat-box"><h3>Realizimi Live</h3><p>{t_real:,.0f} kg</p></div>
                <div class="stat-box"><h3>Ecuria %</h3><p>{total_perc:.1f}%</p></div>
                <div class="stat-box"><h3>Statusi i Kohës</h3><p>{ditet_punes_deri_sot}/{ditet_punes_totale} Ditë</p></div>
                <div class="stat-box"><h3>Çmimi Mesatar</h3><p>{cmimi_mesatar:,.2f} Lekë</p></div>
            </div>

            <div class="trend-section">
                <h2 style="margin-top:0; color: #1a237e; font-size: 18px;">🔍 Krahasimi i Trendeve (Pa të diela)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Lloji i Trendit</th>
                            <th>Vlera e Krahasuar</th>
                            <th>Devijimi / Rritja</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Trendi Linear</strong> (Parashikimi i mbylljes)</td>
                            <td>{projeksioni:,.0f} kg</td>
                            <td class="{'positive' if projeksioni >= t_target else 'negative'}">
                                {projeksioni - t_target:,.0f} kg vs Objektivi
                            </td>
                        </tr>
                        <tr>
                            <td><strong>vs Muaji i Kaluar</strong> (Deri në datën {sot.day})</td>
                            <td>{t_m_kaluar:,.0f} kg</td>
                            <td class="{'positive' if rritja_m >= 0 else 'negative'}">
                                {rritja_m:+.1f}%
                            </td>
                        </tr>
                        <tr>
                            <td><strong>vs Viti i Kaluar</strong> (Deri në datën {sot.day})</td>
                            <td>{t_v_kaluar:,.0f} kg</td>
                            <td class="{'positive' if rritja_v >= 0 else 'negative'}">
                                {rritja_v:+.1f}%
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

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
# MODULI: ASISTENTI AI (Versioni i Plotë me të gjitha Listat)
# ---------------------------------------------------------
elif page == "Asistenti AI":
    # st.title("🛡️ Strategjia e Shitjeve & Agjenda Inteligjente")
    st.title("Strategjia e Shitjeve & Agjenda Inteligjente")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if agj_sel == "Të gjithë":
        st.warning("⚠️ Zgjidhni një agjent në sidebar për të parë planin e plotë.")
    else:
        sot = datetime.now()
        data_sot_str = sot.strftime("%d/%m/%Y")
        df_tmp = df_raw.copy()
        df_tmp.columns = [c.lower() for c in df_tmp.columns]

        # 1. KALKULIMI I REALIZIMIT DHE PLANIT (Logjika juaj origjinale)
        mask_ref = (df_tmp["data"].dt.date >= start_date) & (
            df_tmp["data"].dt.date <= end_date
        )
        df_agj_ref = df_tmp[mask_ref & (df_tmp["forcashitese"] == agj_sel)]
        n_months_ref = max(
            1,
            (end_date.year - start_date.year) * 12
            + (end_date.month - start_date.month),
        )

        kl_target = df_agj_ref.groupby("klienti")["kg"].sum().reset_index()
        kl_target["Target_Muaj"] = (kl_target["kg"] / n_months_ref) * (1 + rritja / 100)

        mask_live = (df_tmp["data"].dt.year == sot.year) & (
            df_tmp["data"].dt.month == sot.month
        )
        df_live_agj = df_tmp[mask_live & (df_tmp["forcashitese"] == agj_sel)]

        kl_real_detajuar = (
            df_live_agj.groupby(["klienti", "data"]).agg({"kg": "sum"}).reset_index()
        )
        statusi_real = kl_real_detajuar.groupby("klienti")["kg"].sum().reset_index()

        full_map = pd.merge(kl_target, statusi_real, on="klienti", how="left").fillna(0)
        full_map["Ecuria"] = full_map["kg_y"] / full_map["Target_Muaj"] * 100
        full_map["Mbetja_KG"] = (full_map["Target_Muaj"] - full_map["kg_y"]).clip(
            lower=0
        )

        # 2. STATISTIKAT KRYESORE
        total_kliente = df_tmp[df_tmp["forcashitese"] == agj_sel]["klienti"].nunique()
        vizitat_count = (
            kl_real_detajuar.groupby("klienti")["data"].nunique().reset_index()
        )
        double_visits = vizitat_count[vizitat_count["data"] > 1]["klienti"].tolist()

        # --- SHPALLJA E STATISTIKAVE ME (i) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Klientë", total_kliente)
        col2.metric("Vizituar (Muaj)", len(statusi_real))
        col3.metric("Pa vizituar", total_kliente - len(statusi_real))
        col4.metric(
            "Double Visits",
            len(double_visits),
            help="Klientë që janë faturuar më shumë se një herë brenda muajit korrent.",
        )

        st.info(
            "ℹ️ **Mbetja në KG** llogaritet si: (Targeti i zgjedhur te Planifikimi) - (Shitjet reale të muajit korrent).",
            icon="💡",
        )
        tab1, tab2, tab3 = st.tabs(
            [
                "🔴 Kritikë (60+ ditë)",
                "🟡 Prapa Planit",
                "🔵 Të Sugjeruar (Pa vizitë këtë muaj)",
            ]
        )

        # FORMATIMI I DATEVE
        def mark_sot_ai(x):
            d = x.strftime("%d/%m/%Y")
            return f"⭐ {d} (SOT)" if d == data_sot_str else d

        # TAB 1: KLIENTET E HUMBUR
        with tab1:
            kufiri_humbjes = sot - pd.Timedelta(days=60)
            blerja_f = (
                df_tmp[df_tmp["forcashitese"] == agj_sel]
                .groupby("klienti")["data"]
                .max()
                .reset_index()
            )
            kl_humbur = blerja_f[blerja_f["data"] < kufiri_humbjes].copy()
            kl_humbur["Blerja e Fundit"] = kl_humbur["data"].apply(mark_sot_ai)
            kl_humbur["Vizito"] = False
            kl_humbur["Pezull"] = False
            ed_humb = st.data_editor(
                kl_humbur[["Vizito", "Pezull", "klienti", "Blerja e Fundit"]],
                key="humb_v3",
                hide_index=True,
                use_container_width=True,
            )

        # TAB 2: RREZIK PLANI
        with tab2:
            rrezik = (
                full_map[(full_map["Ecuria"] < 50) & (full_map["kg_y"] > 0)]
                .sort_values("Target_Muaj", ascending=False)
                .copy()
            )
            rrezik["Vizito"] = False
            rrezik["Pezull"] = False
            ed_rrez = st.data_editor(
                rrezik[["Vizito", "Pezull", "klienti", "Target_Muaj", "Ecuria"]],
                column_config={
                    "Ecuria": st.column_config.NumberColumn(format="%.1f%%")
                },
                key="rrez_v3",
                hide_index=True,
                use_container_width=True,
            )

        # TAB 3: SUGJERIMET (Klientët që s'janë vizituar ende këtë muaj)
        with tab3:
            jo_vizituar = (
                full_map[full_map["kg_y"] == 0]
                .sort_values("Target_Muaj", ascending=False)
                .copy()
            )
            jo_vizituar["Vizito"] = False
            jo_vizituar["Pezull"] = False
            ed_sugj = st.data_editor(
                jo_vizituar[["Vizito", "Pezull", "klienti", "Target_Muaj"]],
                column_config={
                    "Vizito": st.column_config.CheckboxColumn(
                        "Zgjidh",
                        help="Shtoji këta klientë në raportin e vizitave të ditës.",
                    ),
                    "Pezull": st.column_config.CheckboxColumn(
                        "Pezull",
                        help="Lëri për një ditë tjetër, mos i përfshi në ngarkesë.",
                    ),
                    "Target_Muaj": st.column_config.NumberColumn(
                        "Objektivi KG",
                        help="Sasia mesatare historike + rritja e aplikuar.",
                    ),
                },
                key="sugj_v4",
                hide_index=True,
                use_container_width=True,
            )

        # 3. PROCESIMI I SELEKTIMEVE
        s_h = ed_humb[(ed_humb["Vizito"] == True) & (ed_humb["Pezull"] == False)][
            "klienti"
        ].tolist()
        s_r = ed_rrez[(ed_rrez["Vizito"] == True) & (ed_rrez["Pezull"] == False)][
            "klienti"
        ].tolist()
        s_s = ed_sugj[(ed_sugj["Vizito"] == True) & (ed_sugj["Pezull"] == False)][
            "klienti"
        ].tolist()
        lista_finale = list(set(s_h + s_r + s_s))

        st.divider()
        if lista_finale:
            st.success(
                f"✅ Agjenda u krijua me {len(lista_finale)} klientë."
            )  # 3. PROCESIMI I SELEKTIMEVE
        s_h = ed_humb[(ed_humb["Vizito"] == True) & (ed_humb["Pezull"] == False)][
            "klienti"
        ].tolist()
        s_r = ed_rrez[(ed_rrez["Vizito"] == True) & (ed_rrez["Pezull"] == False)][
            "klienti"
        ].tolist()
        s_s = ed_sugj[(ed_sugj["Vizito"] == True) & (ed_sugj["Pezull"] == False)][
            "klienti"
        ].tolist()
        lista_finale = list(set(s_h + s_r + s_s))

        st.divider()
        if lista_finale:
            st.success(f"✅ Agjenda u krijua me {len(lista_finale)} klientë.")

            c_r1, c_r2 = st.columns(2)

            if c_r1.button("📊 Raporti i Klientëve (KG & Vlera)"):
                # Përdorim një çmim mesatar fiks që të mos varet nga skedari CSV nëse ai dështon
                cmimi_ref = 125

                rep_kl = full_map[full_map["klienti"].isin(lista_finale)].copy()
                rep_kl["Vlera"] = rep_kl["Mbetja_KG"] * cmimi_ref

                st.dataframe(
                    rep_kl[["klienti", "Mbetja_KG", "Vlera"]], use_container_width=True
                )

                t_kg = rep_kl["Mbetja_KG"].sum()
                t_vl = rep_kl["Vlera"].sum()
                st.markdown(
                    f"**TOTALI: {t_kg:,.1f} KG | {t_vl:,.1f} Lekë | Çmimi Mes: {t_vl/t_kg if t_kg>0 else 0:,.1f} Lekë**"
                )

            if c_r2.button("📦 Raporti i Artikujve për Ngarkesë"):
                art_data = []
                for k in lista_finale:
                    # Gjejmë mbetjen e KG për këtë klient nga plani
                    mbetja_klientit = full_map[full_map["klienti"] == k][
                        "Mbetja_KG"
                    ].values[0]

                    # Gjejmë çfarë i mungon (Gap Analysis)
                    kufiri_g = sot - pd.Timedelta(days=90)
                    hist = df_tmp[
                        (df_tmp["klienti"] == k) & (df_tmp["data"] < kufiri_g)
                    ]
                    akt = df_tmp[
                        (df_tmp["klienti"] == k) & (df_tmp["data"] >= kufiri_g)
                    ]
                    mungesa = [
                        a
                        for a in hist["artikulli"].unique()
                        if a not in akt["artikulli"].unique()
                    ]

                    # Shpërndajmë mbetjen e KG në artikujt që mungojnë (nëse ka 2 artikuj, secili merr gjysmën)
                    if mungesa:
                        sasia_per_artikull = mbetja_klientit / len(
                            mungesa[:3]
                        )  # Limit dosti 3 artikuj
                        for m in mungesa[:3]:
                            art_data.append(
                                {"Artikulli": m, "Sasia KG": sasia_per_artikull}
                            )
                    else:
                        # Nëse s'ka gap, e llogarisim si sasi totale që duhet shitur nga portofoli ekzistues
                        art_data.append(
                            {
                                "Artikulli": "PORTOFOL DIVERS",
                                "Sasia KG": mbetja_klientit,
                            }
                        )

                if art_data:
                    df_art_f = pd.DataFrame(art_data)
                    raport_artikujt = (
                        df_art_f.groupby("Artikulli")["Sasia KG"].sum().reset_index()
                    )

                    st.dataframe(
                        raport_artikujt.sort_values("Sasia KG", ascending=False),
                        use_container_width=True,
                    )
                    st.markdown(
                        f"**TOTALI I SASISË PËR NGARKESË: {raport_artikujt['Sasia KG'].sum():,.1f} KG**"
                    )
                else:
                    st.info("Nuk u gjetën artikuj specifikë.")
        else:
            st.info("Zgjidhni klientët në tab-et e mësipërme për të gjeneruar planet.")

# ---------------------------------------------------------
# MODULI: ROUTE PLAN AI & OPTIMIZIMI I ITINERAREVE
# ---------------------------------------------------------
elif page == "Route Plan AI":
    st.title("🗺️ Route Plan AI & Optimizimi i Itinerareve")
    st.markdown(
        "Ky modul përdor koordinatat live nga `KlientetListView` për të menaxhuar dhe optimizuar rrugëtimet e agjentëve."
    )

    if df_klientet_regjistri is None:
        st.error(
            "❌ Gabim: Nuk u mundësua ngarkimi i të dhënave nga 'KlientetListView'. Kontrolloni lidhjen me databazën."
        )
    else:
        # 1. Filtrojmë klientët që kanë Statusi == 'Aktiv'
        df_itinerar_aktiv = df_klientet_regjistri[
            df_klientet_regjistri["StatusiAktiv"] == True
        ].copy()

        # 2. Përzgjedhja e Agjentit/Zonës nga regjistri aktual
        zonat_aktuale = sorted(
            df_itinerar_aktiv["ForcaShiteseAktuale"].dropna().unique()
        )

        st.subheader("🔍 Përzgjedhja e Agjentit për Terren")
        zona_zgjedhur = st.selectbox("Zgjidh Zonën / Agjentin Aktual:", zonat_aktuale)

        if zona_zgjedhur:
            # 3. Filtrojmë klientët e këtij agjenti që kanë koordinata të sakta gjeografike
            df_zona = df_itinerar_aktiv[
                (df_itinerar_aktiv["ForcaShiteseAktuale"] == zona_zgjedhur)
                & (df_itinerar_aktiv["Latitude"].notna())
                & (df_itinerar_aktiv["Longitude"].notna())
            ].copy()

            # Streamlit kërkon që emrat e kolonave për hartën të jenë fiks me të vogla
            df_zona.rename(
                columns={"Latitude": "latitude", "Longitude": "longitude"}, inplace=True
            )

            st.divider()
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("🏪 Klientë Aktivë në Regjistër", f"{len(df_zona)}")

            # Llogarisim klientët aktivë të këtij agjenti që nuk kanë koordinata të hedhura në SQL
            kliente_pa_koordinata = len(
                df_itinerar_aktiv[
                    df_itinerar_aktiv["ForcaShiteseAktuale"] == zona_zgjedhur
                ]
            ) - len(df_zona)
            col_m2.metric(
                "📍 Klientë pa Gjeolokacion",
                f"{kliente_pa_koordinata}",
                delta="- Jo në Hartë" if kliente_pa_koordinata > 0 else "Rregullt",
            )

            # 4. Shfaqja e Hartës
            if not df_zona.empty:
                st.subheader(f"🗺️ Harta e Itinerarit: {zona_zgjedhur}")
                st.map(df_zona, size=25, color="#1f77b4")

                # 5. Tabela e detajuar
                st.subheader("📋 Lista e Klientëve dhe Adresat (Qyteti)")
                konfig_tabeles = {
                    "KodiKlient": st.column_config.TextColumn("🔑 Kodi"),
                    "Klienti": st.column_config.TextColumn("🏪 Emri i Klientit"),
                    "Rajoni": st.column_config.TextColumn("📍 Qyteti/Rajoni"),
                    "latitude": st.column_config.NumberColumn(
                        "🌐 Latitude", format="%.5f"
                    ),
                    "longitude": st.column_config.NumberColumn(
                        "🌐 Longitude", format="%.5f"
                    ),
                }

                st.dataframe(
                    df_zona[
                        ["KodiKlient", "Klienti", "Rajoni", "latitude", "longitude"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config=konfig_tabeles,
                )
            else:
                st.warning(
                    f"⚠️ Agjenti '{zona_zgjedhur}' ka klientë aktivë, por asnjëri prej tyre nuk ka koordinata Latitude/Longitude në SQL."
                )

# ---------------------------------------------------------
# MODULI I PLOTË: SHITJET DITORE (Formatim Estetik pa Dhjetore)
# ---------------------------------------------------------
elif page == "Shitjet Ditore":
    import calendar
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime

    # Data aktuale e referencës
    sot = datetime(2026, 5, 16)

    st.title(f"Shitjet Ditore")
    st.markdown(
        f"<h3 style='color: #1a237e; margin-top:-15px;'>Muaji Aktual: {muajt_sq.get(sot.month)} {sot.year} | 👤 Agjenti: {agj_sel}</h3>",
        unsafe_allow_html=True,
    )
    st.divider()

    if df_raw is not None and not df_raw.empty:

        # --- MARRIM DIREKT KOLONËN "kg" TË LLOGARITUR NGA FILLIMI I KODIT ---
        kolona_kg = "kg"

        # --- LLOGARITJA AUTOMATIKE E PERIUDHAVE ---
        vit_aktual = sot.year
        muaj_aktual = sot.month

        if muaj_aktual == 1:
            vit_para_muaj = vit_aktual - 1
            para_muaj = 12
        else:
            vit_para_muaj = vit_aktual
            para_muaj = muaj_aktual - 1

        vit_para_vit = vit_aktual - 1
        para_vit_muaj = muaj_aktual

        # --- EMRAT DINAMIKË PËR METRIKAT DHE LEGJENDËN ---
        emri_muaj_aktual = f"{muajt_sq.get(muaj_aktual).upper()} {vit_aktual}"
        emri_muaj_kaluar = f"{muajt_sq.get(para_muaj).upper()} {vit_para_muaj}"
        emri_vit_kaluar = f"{muajt_sq.get(para_vit_muaj).upper()} {vit_para_vit}"

        # --- FILTRIMET E PËRGJITHSHËM ---
        df_base = df_raw.copy()
        df_base["Data"] = pd.to_datetime(df_base["Data"], errors="coerce")

        if grup_sel != "Të gjitha":
            df_base = df_base[df_base["Grup_Filtri"] == grup_sel]

        if agj_sel != "Të gjithë":
            df_base = df_base[df_base["ForcaShitese"] == agj_sel]

        if klientet_selected:
            df_base = df_base[df_base["Klienti"].isin(klientet_selected)]

        # --- FUNKSIONI I MARRJES SË TË DHËNAVE ---
        def merr_asortimentin_ditore(df_filtri, vit, muaj):
            df_p = df_filtri[
                (df_filtri["Data"].dt.year == vit)
                & (df_filtri["Data"].dt.month == muaj)
            ].copy()
            if not df_p.empty:
                df_p["Dita_Numri"] = df_p["Data"].dt.day
                df_p[kolona_kg] = pd.to_numeric(
                    df_p[kolona_kg], errors="coerce"
                ).fillna(0)
                return df_p.groupby("Dita_Numri")[kolona_kg].sum().to_dict()
            return {}

        data_aktual = merr_asortimentin_ditore(df_base, vit_aktual, muaj_aktual)
        data_para_muaj = merr_asortimentin_ditore(df_base, vit_para_muaj, para_muaj)
        data_para_vit = merr_asortimentin_ditore(df_base, vit_para_vit, para_vit_muaj)

        _, numri_diteve = calendar.monthrange(vit_aktual, muaj_aktual)

        # --- PREGATITJA E KASKADËS ---
        ditet_numerik = list(range(1, numri_diteve + 1))
        ditet_etiketa = [f"{d:02d}" for d in ditet_numerik]

        def llogarit_kaskaden(data_dict):
            vlerat_reale = []
            vlerat_baze = []
            kumulativ = 0.0
            for d in range(1, numri_diteve + 1):
                vlera = data_dict.get(d, 0.0)
                vlerat_baze.append(kumulativ)
                vlerat_reale.append(vlera)
                kumulativ += vlera
            return vlerat_baze, vlerat_reale

        base_aktual, y_aktual = llogarit_kaskaden(data_aktual)
        base_para_muaj, y_para_muaj = llogarit_kaskaden(data_para_muaj)
        base_para_vit, y_para_vit = llogarit_kaskaden(data_para_vit)

        # --- LLOGARITJA E METRIKAVE TOTALE ---
        totali_aktual = sum(y_aktual)
        totali_para_muaj = sum(y_para_muaj)
        totali_para_vit = sum(y_para_vit)

        c1, c2, c3 = st.columns(3)
        ndryshimi_muaj = (
            ((totali_aktual - totali_para_muaj) / totali_para_muaj * 100)
            if totali_para_muaj > 0
            else 0
        )
        ndryshimi_vit = (
            ((totali_aktual - totali_para_vit) / totali_para_vit * 100)
            if totali_para_vit > 0
            else 0
        )

        c1.metric(label=f"Shitjet {emri_muaj_aktual}", value=f"{totali_aktual:,.0f} kg")
        c2.metric(
            label=f"vs {emri_muaj_kaluar}",
            value=f"{totali_para_muaj:,.0f} kg",
            delta=f"{ndryshimi_muaj:+.1f}%",
        )
        c3.metric(
            label=f"vs {emri_vit_kaluar}",
            value=f"{totali_para_vit:,.0f} kg",
            delta=f"{ndryshimi_vit:+.1f}%",
        )
        st.write("")

        # --- NDËRTIMI I GRAFIKUT FINAL ---
        fig = go.Figure()
        gjeresia_kolones = 0.6

        # 1. VIT PARAFRA (P.sh. MAJ 2025)
        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_para_vit,
                base=base_para_vit,
                name=emri_vit_kaluar,
                width=gjeresia_kolones,
                marker_color="rgba(141, 211, 199, 0.55)",
                textposition="none",
                hovertemplate="%{y:,.0f} kg<extra></extra>",  # Formati hover pa dhjetore
            )
        )

        # 2. MUAJI I KALUAR (P.sh. PRILL 2026)
        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_para_muaj,
                base=base_para_muaj,
                name=emri_muaj_kaluar,
                width=gjeresia_kolones,
                marker_color="rgba(0, 105, 92, 0.55)",
                textposition="none",
                hovertemplate="%{y:,.0f} kg<extra></extra>",  # Formati hover pa dhjetore
            )
        )

        # 3. MUAJI AKTUAL (P.sh. MAJ 2026)
        fig.add_trace(
            go.Bar(
                x=ditet_numerik,
                y=y_aktual,
                base=base_aktual,
                name=emri_muaj_aktual,
                width=gjeresia_kolones,
                marker_color="rgba(255, 193, 7, 0.65)",
                # Formatojmë tekstet sipër shtyllave me ndarës mijësh pa dhjetore
                text=[f"{v:,.0f}" if v > 0 else "" for v in y_aktual],
                textposition="outside",
                hovertemplate="%{y:,.0f} kg<extra></extra>",  # Formati hover pa dhjetore
            )
        )

        fig.update_layout(
            title=f"KASKADA KRAHASUESE E SHITJEVE DITORE ({emri_muaj_aktual})",
            barmode="overlay",
            plot_bgcolor="#eef2f3",
            height=650,
            xaxis=dict(
                title="Ditët e muajit",
                tickangle=0,
                type="linear",
                tickmode="array",
                tickvals=ditet_numerik,
                ticktext=ditet_etiketa,
                range=[0.4, numri_diteve + 0.6],
            ),
            yaxis=dict(title="Shitjet (kg)", gridcolor="#ffffff"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Shiko tabelën krahasuese të të dhënave"):
            tabela_df = pd.DataFrame(
                {
                    "Dita": ditet_etiketa,
                    f"{emri_muaj_aktual} (kg)": y_aktual,
                    f"{emri_muaj_kaluar} (kg)": y_para_muaj,
                    f"{emri_vit_kaluar} (kg)": y_para_vit,
                }
            )

            # Formatimi estetik i tabelës Streamlit me ndarës mijëshe pa dhjetore
            st.dataframe(
                tabela_df.style.format(
                    {
                        f"{emri_muaj_aktual} (kg)": "{:,.0f}",
                        f"{emri_muaj_kaluar} (kg)": "{:,.0f}",
                        f"{emri_vit_kaluar} (kg)": "{:,.0f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    else:
        st.error("Të dhënat nuk u ngarkuan dot.")

# ---------------------------------------------------------
# MODULI: KLIENTËT ME SHUMË AGJENTË (Sipas Kodit të Klientit)
# --------------------------------------------------------
elif page == "Klientët me shumë Agjentë" and df_raw is not None:
    st.title("👥 Klientët e Furnizuar nga Më Shumë se Një Agjent")
    st.markdown(
        "Ky modul analizon përplasjet e agjentëve duke u bazuar te **Kodi Unik i Klientit** për periudhën e zgjedhur."
    )

    # Kontrolli i sigurisë nëse kolona ekziston në tabelën df_raw
    if "KodiKlient" not in df_raw.columns:
        st.error(
            "❌ Gabim strukturor: Kolona 'KodiKlient' nuk u gjet në të dhënat e shkarkuara nga SQL Server. Ju lutem kontrolloni nëse e keni shtuar te load_all_data()."
        )
    else:
        # 1. Krijojmë përzgjedhësit e periudhës në formë muaj-vit
        df_raw["VitiMuaji"] = df_raw["Data"].dt.to_period("M")
        lista_muajve = sorted(df_raw["VitiMuaji"].unique())
        opsionet_muajve = {
            m: f"{muajt_sq.get(m.month, m.month)} {m.year}" for m in lista_muajve
        }

        st.subheader("🔍 Zgjidh Periudhën e Analizës")
        col1, col2 = st.columns(2)
        with col1:
            muaji_fillimit = st.selectbox(
                "Nga Muaji:",
                options=lista_muajve,
                index=0,
                format_func=lambda x: opsionet_muajve[x],
            )
        with col2:
            muaji_mbarimit = st.selectbox(
                "Deri te Muaji:",
                options=lista_muajve,
                index=len(lista_muajve) - 1,
                format_func=lambda x: opsionet_muajve[x],
            )

        if muaji_fillimit > muaji_mbarimit:
            st.error(
                "❌ Gabim: 'Nga Muaji' nuk mund të jetë më i madh se 'Deri te Muaji'!"
            )
        else:
            # 2. Filtrimi i të dhënave bazë
            df_filtri = df_raw[
                (df_raw["VitiMuaji"] >= muaji_fillimit)
                & (df_raw["VitiMuaji"] <= muaji_mbarimit)
            ].copy()

            # Sigurohemi që kolonat kyçe nuk janë boshe
            df_filtri = df_filtri[
                df_filtri["KodiKlient"].notna() & df_filtri["ForcaShitese"].notna()
            ]

            # 3. Agregimi: Grupojmë sipas 'KodiKlient' dhe marrim emrin e parë që gjejmë për atë kod
            raporti_df = (
                df_filtri.groupby("KodiKlient")
                .agg(
                    EmriKlientit=(
                        "Klienti",
                        "first",
                    ),  # Merr emrin e parë për atë kod klienti
                    Agjentet=("ForcaShitese", lambda x: ", ".join(sorted(x.unique()))),
                    Numri_Agjenteve=("ForcaShitese", "nunique"),
                    Totale_KG=("kg", "sum"),
                    Vlera_Totale=("Vlera_Historike", "sum"),
                )
                .reset_index()
            )

            # 4. Filtri Kyç: Vetëm kodet që kanë më shumë se 1 agjent unik
            raporti_final = raporti_df[raporti_df["Numri_Agjenteve"] > 1].sort_values(
                by="Numri_Agjenteve", ascending=False
            )

            # Llogarisim numrin total të klientëve unikë që kanë blerë në këtë periudhë historike
            total_kliente_aktive = df_filtri["KodiKlient"].nunique()

            # Llogarisim përqindjen e klientëve në konflikt
            perqindja_konflikt = (
                (len(raporti_final) / total_kliente_aktive * 100)
                if total_kliente_aktive > 0
                else 0
            )

            # 5. Shfaqja e Metrikave të Përgjithshme (Shtuar numri i klientëve aktualë live)
            st.divider()
            m0, m1, m2, m3, m4 = st.columns(5)

            # METRIKA E RE E KËRKUAR: Merr numrin total të klientëve nga regjistri live i SQL
            if df_klientet_regjistri is not None:
                total_regjister_live = len(df_klientet_regjistri)
                m0.metric(
                    label="📋 Regjistri i Klientëve",
                    value=f"{total_regjister_live:,}",
                    help="Numri total i klientëve që ekzistojnë aktualisht në pamjen dbo.KlientetListView në SQL Server.",
                )
            else:
                m0.metric(label="📋 Regjistri i Klientëve", value="Nuk u ngarkua")

            m1.metric(
                label="🏪 Klientë me Blerje",
                value=f"{total_kliente_aktive:,}",
                help="Numri i klientëve unikë që kanë kryer të paktën një blerje gjatë periudhës së zgjedhur.",
            )
            m2.metric(
                label="⚠️ Klientë në Konflikt",
                value=f"{len(raporti_final):,}",
                delta=f"{perqindja_konflikt:.1f}% e totalit",
                delta_color="inverse",
            )
            m3.metric(
                label="⚖️ Total KG e Prekur",
                value=f"{raporti_final['Totale_KG'].sum():,.0f} kg",
            )
            m4.metric(
                label="💰 Vlera në Konflikt",
                value=f"{raporti_final['Vlera_Totale'].sum():,.0f} L",
            )

            # ---------------------------------------------------------
            # 5.5 GRAFIKU AVANCUAR: I PASTRUAR DHE ME EMËRTIME TË REJA
            # ---------------------------------------------------------

            # 1. Agregimi bazë për klientët unikë dhe agjentët unikë në muaj
            st.divider()
            st.subheader("Analiza Korelative")
            df_baze = (
                df_filtri.groupby("VitiMuaji")
                .agg(
                    Kliente_Aktive=("KodiKlient", "nunique"),
                    Nr_Agjenteve=("ForcaShitese", "nunique"),
                )
                .reset_index()
            )

            # 2. Agregimi për sasinë totale, vetëm DEKA dhe vetëm OLIM
            df_total_kg = (
                df_filtri.groupby("VitiMuaji")["kg"]
                .sum()
                .reset_index()
                .rename(columns={"kg": "KG_Total"})
            )
            df_deka_kg = (
                df_filtri[df_filtri["Grup_Filtri"] == "DEKA"]
                .groupby("VitiMuaji")["kg"]
                .sum()
                .reset_index()
                .rename(columns={"kg": "KG_Deka"})
            )
            df_olim_kg = (
                df_filtri[df_filtri["Grup_Filtri"] == "OLIM"]
                .groupby("VitiMuaji")["kg"]
                .sum()
                .reset_index()
                .rename(columns={"kg": "KG_Olim"})
            )

            # Bashkojmë të gjitha të dhënat në një DataFrame të vetëm
            df_grafiku = pd.merge(df_baze, df_total_kg, on="VitiMuaji", how="left")
            df_grafiku = pd.merge(df_grafiku, df_deka_kg, on="VitiMuaji", how="left")
            df_grafiku = pd.merge(df_grafiku, df_olim_kg, on="VitiMuaji", how="left")
            df_grafiku.fillna(0, inplace=True)

            # Renditim të dhënat sipas muajit
            df_grafiku = df_grafiku.sort_values(by="VitiMuaji").reset_index(drop=True)

            # Kthejmë periudhën në etiketë në shqip
            df_grafiku["Muaji_Etiketa"] = df_grafiku["VitiMuaji"].apply(
                lambda x: f"{muajt_sq.get(x.month, x.month)} {x.year}"
            )

            # --- PANEL KONTROLLI I DYFISHTË (I PASTRUAR NGA TEKSTET) ---
            # Ndryshuar emërtimi në 'Agjentë Aktivë'
            opsionet_serive = {
                "Klientë Aktivë": {
                    "kolona": "Kliente_Aktive",
                    "emri": "🏪 Klientë Aktivë",
                    "ngjyra": "#1f77b4",
                },
                "Agjentë Aktivë": {
                    "kolona": "Nr_Agjenteve",
                    "emri": "👤 Agjentë Aktivë",
                    "ngjyra": "#aec7e8",
                },
                "Sasia Totale (KG)": {
                    "kolona": "KG_Total",
                    "emri": "📦 Sasia Totale (KG)",
                    "ngjyra": "#2ca02c",
                },
                "Sasia DEKA (KG)": {
                    "kolona": "KG_Deka",
                    "emri": "🔴 Sasia DEKA (KG)",
                    "ngjyra": "#d62728",
                },
                "Sasia OLIM (KG)": {
                    "kolona": "KG_Olim",
                    "emri": "🟡 Sasia OLIM (KG)",
                    "ngjyra": "#ffbb78",
                },
            }

            col_b1, col_b2 = st.columns(2)

            with col_b1:
                primar_zgjedhur = st.multiselect(
                    label="Zgjidh seritë e majta:",
                    options=list(opsionet_serive.keys()),
                    default=[
                        "Agjentë Aktivë"
                    ],  # Vendosur si default i ri sipas screenshot-it tënd
                    label_visibility="collapsed",
                )

            with col_b2:
                sekondar_zgjedhur = st.multiselect(
                    label="Zgjidh seritë e djathta:",
                    options=list(opsionet_serive.keys()),
                    default=[
                        "Sasia Totale (KG)"
                    ],  # Vendosur si default i ri sipas screenshot-it tënd
                    label_visibility="collapsed",
                )

            # --- MULTI-OPSIONI I SHKALLËZIMIT (I PASTRUAR NGA DIVIDER DHE TITULLI) ---
            lloji_shkallezimit = st.radio(
                label="Lloji i Shkallëzimit:",
                options=[
                    "Vlera Absolute (Shkallë Lineare standarde)",
                    "Vlera Absolute (Shkallë Logaritmike - për diferenca të mëdha)",
                    "Normalizim në % (Çdo seri nistet nga 100% te muaji i parë)",
                ],
                index=0,
                horizontal=True,
                label_visibility="collapsed",  # Fsheh titullin e radio button-it
            )

            perdor_log = "Logaritmike" in lloji_shkallezimit
            perdor_pct = "Normalizim" in lloji_shkallezimit

            # --- LOGJIKA E NORMALIZIMIT NË % ---
            df_vizualizimi = df_grafiku.copy()
            if perdor_pct and len(df_vizualizimi) > 0:
                rreshti_pare = df_vizualizimi.iloc[0]
                for kategoria, info in opsionet_serive.items():
                    vlera_baze = rreshti_pare[info["kolona"]]
                    if vlera_baze > 0:
                        df_vizualizimi[info["kolona"]] = (
                            df_vizualizimi[info["kolona"]] / vlera_baze
                        ) * 100
                    else:
                        df_vizualizimi[info["kolona"]] = 100.0

            # --- NDËRTIMI I GRAFIKUT ME PLOTLY ---
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go

            fig_universal = make_subplots(specs=[[{"secondary_y": not perdor_pct}]])

            # 1. SERITË PËR BOSHTIN PRIMAR (MAJTAS)
            for kategoria in primar_zgjedhur:
                info = opsionet_serive[kategoria]
                custom_hover = (
                    f"<b>%{{x}}</b><br>{info['emri']}: %{{y:,.1f}}%<br>Vlera Reale: %{{customdata:,.0f}}<extra></extra>"
                    if perdor_pct
                    else f"<b>%{{x}}</b><br>{info['emri']}: %{{y:,.0f}}<extra></extra>"
                )

                fig_universal.add_trace(
                    go.Bar(
                        x=df_vizualizimi["Muaji_Etiketa"],
                        y=df_vizualizimi[info["kolona"]],
                        customdata=df_grafiku[info["kolona"]],
                        name=f"{info['emri']}"
                        + (" (% )" if perdor_pct else " (Majtas)"),
                        text=(
                            df_vizualizimi[info["kolona"]].apply(
                                lambda x: f"{x:,.0f}" if x > 1000 else f"{x}"
                            )
                            if (not perdor_log and not perdor_pct)
                            else None
                        ),
                        textposition="outside",
                        marker_color=info["ngjyra"],
                        hovertemplate=custom_hover,
                    ),
                    secondary_y=False,
                )

            # 2. SERITË PËR BOSHTIN SEKONDAR (DJATHTAS)
            for kategoria in sekondar_zgjedhur:
                info = opsionet_serive[kategoria]
                stili_vijes = "solid"
                if "DEKA" in kategoria:
                    stili_vijes = "dash"
                elif "OLIM" in kategoria:
                    stili_vijes = "dashdot"
                elif "Aktivë" in kategoria or "Agjentë" in kategoria:
                    stili_vijes = "dot"

                custom_hover = (
                    f"<b>%{{x}}</b><br>{info['emri']}: %{{y:,.1f}}%<br>Vlera Reale: %{{customdata:,.0f}}<extra></extra>"
                    if perdor_pct
                    else f"<b>%{{x}}</b><br>{info['emri']}: %{{y:,.0f}}<extra></extra>"
                )

                fig_universal.add_trace(
                    go.Scatter(
                        x=df_vizualizimi["Muaji_Etiketa"],
                        y=df_vizualizimi[info["kolona"]],
                        customdata=df_grafiku[info["kolona"]],
                        name=f"{info['emri']}"
                        + (" (% )" if perdor_pct else " (Djathtas)"),
                        mode="lines+markers",
                        line=dict(color=info["ngjyra"], width=3, dash=stili_vijes),
                        marker=dict(size=8),
                        hovertemplate=custom_hover,
                    ),
                    secondary_y=not perdor_pct,
                )

            # --- KONFIGURIMI I TIPIT TË BOSHTIT ---
            lloji_boshtit = "log" if perdor_log else "linear"

            fig_universal.update_layout(
                xaxis_title=None,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(
                    l=20, r=20, t=10, b=20
                ),  # Ulur marzhi lart pasi hoqëm titujt
                height=480,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5
                ),
                barmode="group",
            )

            # Përditësimi i boshteve dhe emërtimeve anësore
            if perdor_pct:
                fig_universal.update_yaxes(
                    title_text="Ecuria Relative (%)",
                    type=lloji_boshtit,
                    showgrid=bool(primar_zgjedhur),
                    gridcolor="rgba(200,200,200,0.15)",
                    secondary_y=False,
                )
            else:
                titulli_majtas = ", ".join(primar_zgjedhur) if primar_zgjedhur else ""
                fig_universal.update_yaxes(
                    title_text=titulli_majtas,
                    type=lloji_boshtit,
                    showgrid=bool(primar_zgjedhur),
                    gridcolor="rgba(200,200,200,0.15)",
                    secondary_y=False,
                )

                if sekondar_zgjedhur:
                    titulli_djathtas = ", ".join(sekondar_zgjedhur)
                    fig_universal.update_yaxes(
                        title_text=titulli_djathtas,
                        type=lloji_boshtit,
                        showgrid=False,
                        secondary_y=True,
                    )

            # Shfaqja e grafikut final
            if primar_zgjedhur or sekondar_zgjedhur:
                st.plotly_chart(fig_universal, use_container_width=True)
            else:
                st.warning(
                    "⚠️ Ju lutem zgjidhni të paktën një seri për të vizatuar grafikun."
                )

            # 6. Shfaqja e Tabelës Kryesore
            st.subheader("📋 Lista e Kodeve të Klientëve me Përplasje Agjentësh")

            if not raporti_final.empty:
                config_kolonave_konflikt = {
                    "KodiKlient": st.column_config.TextColumn("🔑 Kodi Klientit"),
                    "EmriKlientit": st.column_config.TextColumn("🏪 Emri i Klientit"),
                    "Agjentet": st.column_config.TextColumn("👤 Agjentët Furnizues"),
                    "Numri_Agjenteve": st.column_config.NumberColumn(
                        "🔢 Nr. Agjentëve", format="%d"
                    ),
                    "Totale_KG": st.column_config.NumberColumn(
                        "⚖️ Totale KG", format="%d"
                    ),
                    "Vlera_Totale": st.column_config.NumberColumn(
                        "💰 Vlera Totale (Lekë)", format="%d"
                    ),
                }

                # Rregullojmë radhën e kolonave
                raporti_final = raporti_final[
                    [
                        "KodiKlient",
                        "EmriKlientit",
                        "Agjentet",
                        "Numri_Agjenteve",
                        "Totale_KG",
                        "Vlera_Totale",
                    ]
                ]

                st.dataframe(
                    raporti_final,
                    use_container_width=True,
                    hide_index=True,
                    column_config=config_kolonave_konflikt,
                    height=450,
                )

                # 7. Mundësia për shkarkim në CSV
                csv_konflikt = raporti_final.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Shkarko Raportin e Konflikteve (CSV)",
                    data=csv_konflikt,
                    file_name=f"konfliktet_sipas_kodit_{muaji_fillimit}_{muaji_mbarimit}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

                # 8. Detajimi në nivel artikulli (Drill-down sipas Kodit)
                st.divider()
                st.subheader("🔍 Analizë e Detajuar për një Klient specifik")

                # Krijojmë një listë përzgjedhjeje që tregon "Kodi - Emri" për menaxherin
                raporti_final["Kodi_Emri"] = (
                    raporti_final["KodiKlient"].astype(str)
                    + " - "
                    + raporti_final["EmriKlientit"]
                )
                klienti_zgjedhur_opsion = st.selectbox(
                    "Zgjidh Kodin dhe Emrin e klientit:",
                    options=raporti_final["Kodi_Emri"].unique(),
                )

                if klienti_zgjedhur_opsion:
                    # Shkëputim kodin e pastër nga stringu i përzgjedhur
                    kodi_per_filtrim = klienti_zgjedhur_opsion.split(" - ")[0]

                    df_detaje = (
                        df_filtri[df_filtri["KodiKlient"] == kodi_per_filtrim]
                        .groupby(["ForcaShitese", "kat", "Artikulli"])
                        .agg(Sasia_KG=("kg", "sum"), Vlera=("Vlera_Historike", "sum"))
                        .reset_index()
                    )

                    st.dataframe(
                        df_detaje.style.format(
                            {"Sasia_KG": "{:,.1f}", "Vlera": "{:,.0f} L"}
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.success(
                    "🟢 Nuk u gjet asnjë kod klienti i furnizuar nga më shumë se një agjent për këtë periudhë."
                )

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
