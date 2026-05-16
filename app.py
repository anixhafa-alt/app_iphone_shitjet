import streamlit as st

import pandas as pd

from datetime import datetime

import base64

# 1. Konfigurimi i faqes

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


# --- SISTEMI I SIGURISE (LOGIN) ---


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


def password_entered():

    if st.session_state["password"] == "admin123":

        st.session_state["password_correct"] = True

        del st.session_state["password"]

    else:

        st.session_state["password_correct"] = False


if not check_password():

    st.stop()

st.sidebar.warning("V 1.0.9 - Live Update")
# --- NAVIGIMI ---

st.sidebar.title("🧭 Menuja Kryesore")

page = st.sidebar.radio(
    "Zgjidh Modulin:",
    [
        "Planifikimi",
        "Realizimi",
        "Mundësitë",
        "Historiku",
        "Asistenti AI",
        "Route Plan AI",
    ],
)


# --- NGARKIMI I TE DHENAVE ---


@st.cache_data(ttl=600)
def load_all_data():

    try:
        # A. Lidhja me SQL
        conn = st.connection("sql", type="sql")
        df_sql = conn.query(
            "SELECT Data, ForcaShitese, Klienti, KodiArt, Artikulli, Sasia, VleraRresht FROM dbo.GetRaportiMadhView"
        )
        df_sql.columns = df_sql.columns.str.strip()
        df_sql["Data"] = pd.to_datetime(df_sql["Data"], errors="coerce")

        # B. Lidhja me Excel (Marrim edhe kolonën e statusit)
        df_map = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
        df_map.columns = df_map.columns.str.strip()

        # Ruajmë statusin por NUK e filtrojmë këtu
        df_map = df_map[["KODI", "KATEG.", "KG/SKU", "NGA LISTA E CMIMEVE"]].copy()
        df_map["KODI"] = df_map["KODI"].astype(str).str.strip()

        # C. Merge me "left" (që të mos humbasim asnjë shitje nga SQL)
        df = pd.merge(df_sql, df_map, left_on="KodiArt", right_on="KODI", how="left")

        # D. Kalkulimet
        df["kg"] = df["Sasia"] * df["KG/SKU"].fillna(0)
        df.rename(
            columns={"KATEG.": "kat", "NGA LISTA E CMIMEVE": "statusi"}, inplace=True
        )
        df["Vlera_Historike"] = pd.to_numeric(
            df["VleraRresht"], errors="coerce"
        ).fillna(0)
        df["kat"] = df["kat"].fillna("ETJ")
        df["statusi"] = df["statusi"].fillna(
            "inaktiv"
        )  # Nëse nuk është në listë, e konsiderojmë inaktiv

        # Klasifikimi i grupeve
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
        st.error(f"Gabim teknik: {e}")
        return None


df_raw = load_all_data()


# 1. Lexojmë lidhjen Produkt -> Kod Kategori (Sheet 'produktet')
try:
    df_link = pd.read_excel("produkte+.xlsx", sheet_name="produktet")
    # Përdorim emrat e saktë nga fotoja: KODI dhe KATEG.
    df_link = df_link[["KODI", "KATEG."]].rename(
        columns={"KODI": "KodiArt", "KATEG.": "KOD KAT"}
    )

    # --- FILTRI I RI: Vetëm artikujt AKTIVË ---
    # Përdorim str.upper() për të qenë të sigurt që kapim 'AKTIV', 'Aktiv' etj.
    if "NGA LISTA E CMIMEVE" in df_link.columns:
        df_link = df_link[
            df_link["NGA LISTA E CMIMEVE"].astype(str).str.upper().str.strip()
            == "AKTIV"
        ].copy()

except Exception as e:
    st.error(f"Gabim te sheet-i 'produktet': {e}")
    df_link = None

# 2. Lexojmë emrin e plotë të Kategorisë (Sheet 'kat_prod')
try:
    df_names = pd.read_excel("produkte+.xlsx", sheet_name="kat_prod")
    # Përdorim emrat e saktë nga fotoja: KOD KAT dhe EMRI KAT
    df_names = df_names[["KOD KAT", "EMRI KAT"]]
except Exception as e:
    st.error(f"Gabim te sheet-i 'kat_prod': {e}")
    df_names = None

# 3. BASHKIMI I MADH (Triple Merge)
if df_raw is not None and df_link is not None:
    # A. Lidhim SQL (KodiArt) me Kategorinë (KOD KAT)
    df_raw = pd.merge(df_raw, df_link, on="KodiArt", how="left")

    # B. Lidhim Kodin e Kategorisë me Emrin e Plotë (EMRI KAT)
    if df_names is not None:
        df_raw = pd.merge(df_raw, df_names, on="KOD KAT", how="left")

        # C. Krijojmë kolonën finale 'kat' që përdor pjesa tjetër e kodit
        # Nëse emri mungon, përdorim kodin, nëse edhe kodi mungon "Pa Kategori"
        df_raw["kat"] = (
            df_raw["EMRI KAT"].fillna(df_raw["KOD KAT"]).fillna("Pa Kategori")
        )

# Kontrolli i Datës dhe Orës së Fundit të Përditësimit
if not df_raw.empty:
    kolona_date = [c for c in df_raw.columns if c.lower() == "data"]

    if kolona_date:
        emer_kolone = kolona_date[0]
        datet_konvertuara = pd.to_datetime(df_raw[emer_kolone], errors="coerce")
        data_maksimale = datet_konvertuara.max()

        sot_data = datetime.now().date()

        st.sidebar.subheader("🔄 Statusi i Sinkronizimit")

        if pd.notnull(data_maksimale):
            # Formati i ri përfshin Datën dhe Orën (%d/%m/%Y %H:%M)
            koha_formatuar = data_maksimale.strftime("%d/%m/%Y %H:%M:%S")

            if data_maksimale.date() == sot_data:
                st.sidebar.success(
                    f"🟢 Lidhja SQL: LIVE\n- Fat. e fundit: {koha_formatuar}"
                )
            else:
                vonesa = (sot_data - data_maksimale.date()).days
                st.sidebar.warning(
                    f"🟡 Lidhja SQL: OK\n\n"
                    f"Përditësimi i fundit:\n{koha_formatuar}\n\n"
                    f"Vonesa: {vonesa} ditë pa faturime."
                )

        # --- BUTONI PËR REFRESH TË PLOTË ---
        st.sidebar.markdown("---")
        if st.sidebar.button(
            "🔄 Rifresko nga SQL Server",
            use_container_width=True,
            help="Klikoni për të tërhequr faturat më të fundit live nga databaza qendrore.",
        ):
            st.cache_data.clear()
            st.rerun()

    else:
        st.sidebar.error("⚠️ Nuk u gjet kolona 'DATA' në tabelë.")

# --- SIDEBAR (E përbashkët për të gjitha modulet) ---
st.sidebar.header("⚙️ Kontrolli i Planit")

# 1. Kontrollojmë nëse df_raw ka të dhëna përpara se të vazhdojmë
if df_raw is not None and not df_raw.empty:
    # Ruajtja dhe Ngarkimi i vlerave nga Session State nëse të dhënat ekzistojnë
    if "start_d" not in st.session_state:
        st.session_state["start_d"] = df_raw["Data"].min().date()
    if "end_d" not in st.session_state:
        st.session_state["end_d"] = df_raw["Data"].max().date()
    if "rritja_val" not in st.session_state:
        st.session_state["rritja_val"] = 10
else:
    # Nëse nuk lidhet, shfaqim një mesazh miqësor dhe ndalojmë ekzekutimin e mëtutjeshëm
    st.error(
        "⚠️ Nuk u morën dot të dhënat nga databaza. Kontrollo lidhjen dhe secrets.toml."
    )
    st.info("Aplikacioni po punon, por nuk ka të dhëna për të shfaqur.")
    st.stop()  # Ky rresht ndalon pjesën tjetër të kodit që të mos nxjerrë errore të tjera


# 2. Ndërtimi i Menusë (Si në foto)
date_range = st.sidebar.date_input(
    "Periudha referente:",
    value=(st.session_state["start_d"], st.session_state["end_d"]),
    key="date_input_key",
)

# Përditësojmë session_state kur ndryshon data
if isinstance(date_range, tuple) and len(date_range) == 2:
    st.session_state["start_d"], st.session_state["end_d"] = date_range

rritja = st.sidebar.number_input(
    "Rritja e planit (%)", value=st.session_state["rritja_val"], key="rritja_input"
)
st.session_state["rritja_val"] = rritja

grup_sel = st.sidebar.selectbox("Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"])

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

# Ruajmë datat aktuale për përdorim në Sidebar
start_date = st.session_state["start_d"]
end_date = st.session_state["end_d"]

# Butoni i Logout në fund të Sidebar
st.sidebar.divider()
if st.sidebar.button("Log Out"):
    st.session_state["password_correct"] = False
    st.rerun()

# --- INFO MBI FILTRAT (Shtoje në Sidebar ose në krye të faqes) ---
with st.sidebar.expander("ℹ️ Detajet e përzgjedhjes", expanded=True):
    # Llogarisim numrin e artikujve në bazë të statusit
    nr_aktiv = df_raw[df_raw["statusi"].astype(str).str.upper() == "AKTIV"][
        "Artikulli"
    ].nunique()
    nr_inaktiv = df_raw[df_raw["statusi"].astype(str).str.upper() != "AKTIV"][
        "Artikulli"
    ].nunique()

    st.write(
        f"📅 **Periudha:** {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    )
    st.write(f"👤 **Agjenti:** {agj_sel}")
    st.write(
        f"🏢 **Klientë të zgjedhur:** {len(klientet_selected) if klientet_selected else 'Të gjithë'}"
    )
    st.write(f"📦 **Artikuj Aktivë:** {nr_aktiv}")
    st.write(f"🛑 **Artikuj Inaktivë:** {nr_inaktiv}")

    if page == "Mundësitë":
        st.caption(
            "⚠️ Në këtë modul, artikujt inaktivë janë përjashtuar automatikisht."
        )
    elif page == "Planifikimi":
        st.caption(
            "✅ Në këtë modul, janë përfshirë të gjithë artikujt për të mbajtur volumin e kategorisë."
        )


# --- FUNDI I SIDEBAR ---

# ---------------------------------------------------------
# MODULI: HISTORIKU
# ---------------------------------------------------------
if page == "Historiku":
    st.title("📚 Historiku i Shitjeve & Analiza e Artikujve")

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

    # --- SIDEBAR ---

    # st.sidebar.header("⚙️ Kontrolli")

    # if st.sidebar.button("Log Out"):

    # st.session_state["password_correct"] = False

    #  st.rerun()

    # min_d, max_d = df_raw['Data'].min().date(), df_raw['Data'].max().date()

    # date_range = st.sidebar.date_input("Periudha referente:", value=(min_d, max_d))

    # start_date, end_date = date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (min_d, max_d)

    # rritja = st.sidebar.number_input("Rritja e planit (%)", value=10)

    # grup_sel = st.sidebar.selectbox("Filtro Grupin:", ["Të gjitha", "OLIM", "ETJ", "DEKA"])

    # agj_list = sorted([str(x) for x in df_raw['ForcaShitese'].unique() if x not in ['nan', 'None']])

    # agj_sel = st.sidebar.selectbox("Filtro Agjentin:", ["Të gjithë"] + agj_list)

    # k_list = df_raw[df_raw['ForcaShitese'] == agj_sel]['Klienti'].unique() if agj_sel != "Të gjithë" else #df_raw['Klienti'].unique()

    # klientet_selected = st.sidebar.multiselect("Zgjidh Klientin:", sorted(list(k_list)))

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

    gp["Cmimi_Mes_Periudhes"] = gp["Vlera_Historike"] / gp["kg"].replace(0, 1)

    gp = gp.merge(last_prices, on="KodiArt", how="left")

    gp["Plani_KG"] = (gp["kg"] / n_months) * (1 + rritja / 100)

    gp["Vlera_Planifikuar"] = gp["Plani_KG"] * gp["Cmimi_Fundit_Artikulli"].fillna(
        gp["Cmimi_Mes_Periudhes"]
    )

    # --- TITULLI DHE METRICS (Titulli tashmë është muaji korrent) ---
    st.title(f"🎯 Plani: {muajt_sq.get(sot.month)} {sot.year}")

    st.info(f"📅 Update i fundit: **{data_fundit_db}** | Grupi: **{grup_sel}**")

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
    st.title(f"📈 Realizimi Live - {muajt_sq.get(sot.month)} {sot.year}")

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
        c1, c2, c3, c4 = st.columns(4)
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
                .stat-box {{ background: white; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1a237e; width: 23%; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
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
                <div class="filter-item">📅 Referenca: <strong>{start_date.strftime('%d/%m/%y')} - {end_date.strftime('%d/%m/%y')}</strong></div>
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
    st.title("🎯 Analiza e Mundësive (Gap Analysis)")

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
    st.title("🛡️ Strategjia e Shitjeve & Agjenda Inteligjente")

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
# MODULI I RI: ROUTE PLAN AI (Plani Strategjik Ditor)
# ---------------------------------------------------------
elif page == "Route Plan AI":
    st.title("📅 Route Plan AI")
    st.markdown(
        """
        <style> .stTooltipIcon { display: inline-block; } </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader(
        f"Strategjia e Shpërndarjes",
        help="""
        Ky plan ndan portofolin tuaj në 26 ditë pune:
        1. Ditët e para (1-10) janë prioritare për klientët në 'Humbje' dhe 'Rrezik'.
        2. Sasia KG bazohet në mbetjen tuaj të planit mujor.
        3. Gap Analysis tregon kodet që klienti s'i ka blerë në 90 ditët e fundit.
    """,
    )
    if agj_sel == "Të gjithë":
        st.warning(
            "⚠️ Ju lutem përzgjidhni një agjent specifik për të gjeneruar rrugëtimin ditor."
        )
    else:
        # Përgatitja e të dhënave bazë
        df_tmp = df_raw.copy()
        df_tmp.columns = [c.lower() for c in df_tmp.columns]

        # 1. Identifikimi i Klientëve sipas 3 Kategorive (Logjika e Modulit të parë)
        # ---------------------------------------------------------------------
        mask_ref = (df_tmp["data"].dt.date >= start_date) & (
            df_tmp["data"].dt.date <= end_date
        )
        df_agj = df_tmp[mask_ref & (df_tmp["forcashitese"] == agj_sel)]

        # Llogarisim Targetin
        n_months_ref = max(
            1,
            (end_date.year - start_date.year) * 12
            + (end_date.month - start_date.month),
        )
        kl_target = df_agj.groupby("klienti")["kg"].sum().reset_index()
        kl_target["Target_Muaj"] = (kl_target["kg"] / n_months_ref) * (1 + rritja / 100)

        # Kategorizimi
        # A: Kritikë (nuk kanë blerë > 60 ditë)
        kufiri_humbjes = datetime.now() - pd.Timedelta(days=60)
        blerja_fundit = (
            df_tmp[df_tmp["forcashitese"] == agj_sel]
            .groupby("klienti")["data"]
            .max()
            .reset_index()
        )
        kl_kritike = blerja_fundit[blerja_fundit["data"] < kufiri_humbjes][
            "klienti"
        ].tolist()

        # B: Në Rrezik (Realizimi aktual < 50%) - Për këtë plan marrim gjithë listën e targetuar
        kl_target["kategoria"] = "Stabilë"
        kl_target.loc[kl_target["klienti"].isin(kl_kritike), "kategoria"] = "Kritikë"
        # Në rrezik i konsiderojmë ata me target të lartë (> mesatarja)
        limit_rrezik = kl_target["Target_Muaj"].median()
        kl_target.loc[
            (kl_target["Target_Muaj"] > limit_rrezik)
            & (kl_target["kategoria"] != "Kritikë"),
            "kategoria",
        ] = "Në Rrezik"

        # 2. Krijimi i Kalendarit (26 Ditë Pune)
        # ---------------------------------------------------------------------
        klientet_total = kl_target.sort_values(
            by=["kategoria", "Target_Muaj"], ascending=[True, False]
        )
        numri_klienteve = len(klientet_total)
        kliente_per_dite = max(1, numri_klienteve // 26)  # Supozojmë 26 ditë pune

        st.subheader(
            f"📊 Strategjia për {agj_sel}: {numri_klienteve} klientë të shpërndarë në muaj"
        )

        dita_zgjedhur = st.slider("Zgjidh ditën e punës (1-26):", 1, 26, 1)

        # Ndarja e klientëve në grupe ditore
        start_idx = (dita_zgjedhur - 1) * kliente_per_dite
        end_idx = start_idx + kliente_per_dite
        if dita_zgjedhur == 26:
            end_idx = numri_klienteve  # Ditën e fundit marrim mbetjen

        klientet_e_dites = klientet_total.iloc[start_idx:end_idx]

        # 3. Shfaqja e Planit Ditor
        # ---------------------------------------------------------------------
        st.info(f"📍 Plani për Ditën e Punës #{dita_zgjedhur}")

        for _, row in klientet_e_dites.iterrows():
            kl = row["klienti"]
            kat = row["kategoria"]
            target = row["Target_Muaj"]

            # Përcaktimi i ngjyrës sipas kategorisë
            color = (
                "red"
                if kat == "Kritikë"
                else "orange" if kat == "Në Rrezik" else "green"
            )

            with st.expander(f"🏢 {kl} - Kategoria: {kat}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**Objektivi i Shitjes:** {target:,.1f} KG")

                    # Logjika "Çfarë t'i shesësh" (Gap Analysis 90 ditë)
                    kufiri_gap = datetime.now() - pd.Timedelta(days=90)
                    hist = df_tmp[
                        (df_tmp["klienti"] == kl) & (df_tmp["data"] < kufiri_gap)
                    ]
                    akt = df_tmp[
                        (df_tmp["klienti"] == kl) & (df_tmp["data"] >= kufiri_gap)
                    ]
                    mungojne = [
                        a
                        for a in hist["artikulli"].unique()
                        if a not in akt["artikulli"].unique()
                    ]

                    if mungojne:
                        st.write(f"🛒 **Artikujt Prioritarë:**")
                        for art in mungojne[:3]:
                            st.write(f"- {art}")
                    else:
                        st.write(
                            "🛒 **Artikujt Prioritarë:** Fokus te rritja e volumit të artikujve bazë."
                        )

                with c2:
                    st.write("**Udhëzim:**")
                    if kat == "Kritikë":
                        st.error("Rikuperim! Klienti rrezikon humbjen totale.")
                    elif kat == "Në Rrezik":
                        st.warning("Mbrojtje! Duhet mbuluar mbetja e planit.")
                    else:
                        st.success("Rritje! Sugjeroni artikuj të rinj.")

        # 4. Eksporti i Planit të Plotë
        st.divider()
        if st.button("📥 Shkarko Planin e Plotë 26-Ditor (Excel)"):
            # Krijojmë një kopje për eksport me kolonën e ditës
            export_df = klientet_total.copy()
            export_df["Dita e Punes"] = [
                (i // kliente_per_dite) + 1 for i in range(len(export_df))
            ]
            export_df.loc[export_df["Dita e Punes"] > 26, "Dita e Punes"] = 26

            csv = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Kliko këtu për të shkarkuar",
                csv,
                f"Route_Plan_{agj_sel}.csv",
                "text/csv",
            )
