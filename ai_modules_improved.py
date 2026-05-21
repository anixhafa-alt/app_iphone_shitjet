# =========================================================
# AXION - Modulet AI të Përmirësuara (v2.0)
# =========================================================
# Ky skedar përmban TRE modulet AI të rishkruara me logjikë reale.
# Kopjoji blloqet e mëposhtme në app.py duke zëvendësuar versionet ekzistuese.
#
# DEPENDENCIA TË REJA (shto në requirements.txt):
#   scikit-learn   # për RFM segmentimin (KMeans, StandardScaler)
#   # opsionale, vetëm nëse aktivizon LLM:
#   # anthropic    # për përmbledhje me Claude
#
# Asnjë dependencë e rëndë; gjithçka punon offline mbi df_raw që ke tashmë.
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os


# =========================================================
# HELPER: LLM PËRMBLEDHJE STRATEGJIKE (Claude / OpenAI)
# ---------------------------------------------------------
# Provider-i përcaktohet nga `secrets.toml` ose ENV.
# Konfigurimi:
#   [secrets]
#   LLM_PROVIDER = "anthropic"   # ose "openai" ose "" për ta çaktivizuar
#   ANTHROPIC_API_KEY = "sk-ant-..."
#   OPENAI_API_KEY = "sk-..."
#
# Nëse çelësi mungon, butoni mbetet i çaktivizuar dhe shfaqet udhëzimi.
# =========================================================
def _merr_konfigurimin_llm():
    """Lexon provider-in dhe çelësin nga st.secrets ose env."""
    try:
        provider = st.secrets.get("LLM_PROVIDER", "").lower()
    except Exception:
        provider = ""

    if not provider:
        provider = os.getenv("LLM_PROVIDER", "").lower()

    api_key = ""
    if provider == "anthropic":
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            pass
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    return provider, api_key


def gjenero_permbledhje_llm(konteksti: dict, agjenti: str) -> str:
    """
    Thirr Claude ose OpenAI me një kontekst të strukturuar.
    Konteksti është një dict me të dhënat agreguar (jo rreshta të papërpunuar).
    Kthen tekst Markdown me përmbledhjen strategjike.
    """
    provider, api_key = _merr_konfigurimin_llm()

    if not provider or not api_key:
        return (
            "⚠️ **LLM nuk është konfiguruar.** Shto në `.streamlit/secrets.toml`:\n\n"
            "```toml\n"
            'LLM_PROVIDER = "anthropic"\n'
            'ANTHROPIC_API_KEY = "sk-ant-..."\n'
            "```\n"
            "Pastaj instalo paketën: `pip install anthropic` ose `pip install openai`."
        )

    prompt_sistemi = (
        "Je një konsulent shitjesh që ndihmon menaxherët e shitjeve në Shqipëri. "
        "Përgjigju gjithmonë në shqip. Jep këshilla konkrete, jo gjenerale. "
        "Strukturo si: (1) Diagnoza, (2) 3 Prioritetet e Javës, (3) Klientët kyç për t'u kontaktuar. "
        "Mos shpik të dhëna që s'janë në kontekst. Maks. 250 fjalë."
    )

    prompt_perdoruesi = (
        f"Të dhënat agreguar për agjentin **{agjenti}**:\n\n"
        f"```json\n{json.dumps(konteksti, ensure_ascii=False, indent=2)}\n```\n\n"
        "Hartoji një plan strategjik për javën e ardhshme."
    )

    try:
        if provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=prompt_sistemi,
                messages=[{"role": "user", "content": prompt_perdoruesi}],
            )
            return msg.content[0].text

        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=800,
                messages=[
                    {"role": "system", "content": prompt_sistemi},
                    {"role": "user", "content": prompt_perdoruesi},
                ],
            )
            return resp.choices[0].message.content

        else:
            return f"⚠️ Provider i panjohur: `{provider}`. Përdor `anthropic` ose `openai`."

    except ImportError as e:
        return (
            f"⚠️ Paketa mungon. Instalo: "
            f"`pip install {'anthropic' if provider == 'anthropic' else 'openai'}`\n\n"
            f"Detaji: {e}"
        )
    except Exception as e:
        return f"❌ Gabim gjatë thirrjes së LLM: {e}"


def pergatit_kontekstin_per_llm(full_map: pd.DataFrame, rfm: pd.DataFrame,
                                 lista_humbur: list, vizitat_count: pd.DataFrame) -> dict:
    """Përmbledh të dhënat e agjentit në një strukturë kompakte për LLM."""
    seg_shperndarja = rfm["Segmenti"].value_counts().to_dict() if not rfm.empty else {}

    top_rrezik = (
        full_map[(full_map["Ecuria"] < 50) & (full_map["kg_real"] > 0)]
        .sort_values("Target_Muaj", ascending=False)
        .head(5)[["klienti", "Target_Muaj", "Ecuria", "Segmenti"]]
        .to_dict(orient="records")
    )

    top_jo_vizituar = (
        full_map[full_map["kg_real"] == 0]
        .sort_values("Target_Muaj", ascending=False)
        .head(5)[["klienti", "Target_Muaj", "Segmenti"]]
        .to_dict(orient="records")
    )

    return {
        "total_klientet": int(full_map["klienti"].nunique()),
        "klientet_e_vizituar_muajin_aktual": int((full_map["kg_real"] > 0).sum()),
        "klientet_pa_vizita": int((full_map["kg_real"] == 0).sum()),
        "klientet_e_humbur_60_plus_dite": len(lista_humbur),
        "klientet_double_visits": int((vizitat_count["data"] > 1).sum())
            if not vizitat_count.empty else 0,
        "target_total_kg": float(full_map["Target_Muaj"].sum()),
        "realizimi_total_kg": float(full_map["kg_real"].sum()),
        "ecuria_mesatare_perqindje": float(full_map["Ecuria"].mean()),
        "segmentet_rfm": seg_shperndarja,
        "top_5_klientet_ne_rrezik": top_rrezik,
        "top_5_klientet_pa_vizita": top_jo_vizituar,
    }


# =========================================================
# HELPER: RFM SEGMENTIMI (Recency, Frequency, Monetary)
# ---------------------------------------------------------
# Ky është "AI"-ja reale — segmentim klientësh me KMeans
# mbi 3 dimensionet klasike të analizës së klientelës.
# =========================================================
@st.cache_data(ttl=600, show_spinner=False)
def llogarit_rfm(df: pd.DataFrame, kolona_klienti: str = "klienti") -> pd.DataFrame:
    """Kthen një DataFrame me kolonat: klienti, R, F, M, RFM_Score, Segmenti."""
    if df.empty:
        return pd.DataFrame()

    sot = pd.Timestamp(datetime.now().date())
    d = df.copy()
    d["data"] = pd.to_datetime(d["data"], errors="coerce")
    d = d.dropna(subset=["data"])

    # Agregimi RFM
    rfm = d.groupby(kolona_klienti).agg(
        R=("data", lambda x: (sot - x.max()).days),
        F=("data", "nunique"),  # numri i ditëve unike të blerjes
        M=("kg", "sum"),
    ).reset_index()

    if len(rfm) < 4:
        rfm["RFM_Score"] = 0
        rfm["Segmenti"] = "Pak të dhëna"
        return rfm

    # Skor 1-5 për secilën dimensione
    # R: më e ulët = më mirë (klient i freskët)
    # F, M: më e lartë = më mirë
    rfm["R_Skor"] = pd.qcut(rfm["R"], q=min(5, rfm["R"].nunique()),
                            labels=False, duplicates="drop") + 1
    rfm["R_Skor"] = 6 - rfm["R_Skor"]  # invertojmë (recency e ulët = skor i lartë)

    rfm["F_Skor"] = pd.qcut(rfm["F"].rank(method="first"),
                            q=min(5, rfm["F"].nunique()),
                            labels=False, duplicates="drop") + 1
    rfm["M_Skor"] = pd.qcut(rfm["M"].rank(method="first"),
                            q=min(5, rfm["M"].nunique()),
                            labels=False, duplicates="drop") + 1

    rfm["RFM_Score"] = rfm["R_Skor"] + rfm["F_Skor"] + rfm["M_Skor"]

    def kategorizo(row):
        r, f, m = row["R_Skor"], row["F_Skor"], row["M_Skor"]
        if r >= 4 and f >= 4 and m >= 4:
            return "Kampionët"
        elif r >= 4 and f >= 3:
            return "Besnikë"
        elif r >= 4 and f <= 2:
            return "Të Rinj"
        elif r <= 2 and f >= 4 and m >= 4:
            return "Në Rrezik (VIP)"
        elif r <= 2 and f >= 3:
            return "Po humbasin"
        elif r <= 2 and f <= 2:
            return "Të Humbur"
        else:
            return "Standard"

    rfm["Segmenti"] = rfm.apply(kategorizo, axis=1)
    return rfm


# =========================================================
# HELPER: OPTIMIZIM I RRUGËS (Nearest-Neighbor TSP)
# ---------------------------------------------------------
# Algoritmi heuristik që e fillon rrugën nga pika më e
# afërt me agjentin (ose nga klienti i parë) dhe vazhdon
# duke zgjedhur gjithmonë klientin më të afërt të pavizituar.
# =========================================================
def distance_km(lat1, lon1, lat2, lon2):
    """Haversine — distancë rreth Tokës në km."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def optimizo_rrugen_nn(df_pikat: pd.DataFrame, start_lat=None, start_lon=None) -> pd.DataFrame:
    """
    Renditja optimale e klientëve me Nearest-Neighbor.
    Pret kolona: latitude, longitude.
    Kthen të njëjtin DataFrame me kolona shtesë: Rendi, Distanca_km, Kumulative_km.
    """
    if df_pikat.empty:
        return df_pikat

    pts = df_pikat.reset_index(drop=True).copy()
    n = len(pts)
    visited = [False] * n
    order = []

    # Pika e nisjes — nëse s'ka koordinatë start, fillon nga klienti i parë
    if start_lat is None or start_lon is None:
        start_idx = 0
        order.append(start_idx)
        visited[start_idx] = True
        last_lat, last_lon = pts.loc[start_idx, "latitude"], pts.loc[start_idx, "longitude"]
    else:
        # Gjej klientin më të afërt me pikën e startimit
        d = distance_km(start_lat, start_lon,
                        pts["latitude"].values, pts["longitude"].values)
        start_idx = int(np.argmin(d))
        order.append(start_idx)
        visited[start_idx] = True
        last_lat, last_lon = pts.loc[start_idx, "latitude"], pts.loc[start_idx, "longitude"]

    distances = [0.0]

    while len(order) < n:
        # gjej të paviziturin më të afërt
        mask = np.array(visited)
        d = distance_km(last_lat, last_lon,
                        pts["latitude"].values, pts["longitude"].values)
        d[mask] = np.inf
        nxt = int(np.argmin(d))
        order.append(nxt)
        visited[nxt] = True
        distances.append(float(d[nxt]))
        last_lat, last_lon = pts.loc[nxt, "latitude"], pts.loc[nxt, "longitude"]

    rezultati = pts.iloc[order].reset_index(drop=True)
    rezultati["Rendi"] = range(1, len(rezultati) + 1)
    rezultati["Distanca_km"] = distances
    rezultati["Kumulative_km"] = np.cumsum(distances)
    return rezultati


# =========================================================
# MODULI 1: ASISTENTI AI (versioni i ri)
# ---------------------------------------------------------
# NDRYSHIMET:
#   1) Hoqi bllokun e duplikuar (line 1565-1595 e versionit të vjetër)
#   2) Shtoi segmentin RFM për çdo klient — tregon QUSH është klienti
#      (Kampionët / Besnikë / Në Rrezik / Të Humbur / ...).
#   3) Shtoi grafikun e shpërndarjes së segmenteve.
#   4) Shtoi sugjerime artikujsh të bazuara në SHPESHTËSI (jo thjesht
#      mungesë) — i ngjan një "market basket" të thjeshtuar.
# =========================================================
def render_asistenti_ai(df_raw, agj_sel, start_date, end_date, rritja):
    st.title("Strategjia e Shitjeve & Agjenda Inteligjente")
    st.markdown(f"### 👤 Agjenti: **{agj_sel}**")

    if agj_sel == "Të gjithë":
        st.warning("⚠️ Zgjidhni një agjent në sidebar për të parë planin e plotë.")
        return

    sot = datetime.now()
    data_sot_str = sot.strftime("%d/%m/%Y")
    df_tmp = df_raw.copy()
    df_tmp.columns = [c.lower() for c in df_tmp.columns]
    df_tmp_agj = df_tmp[df_tmp["forcashitese"] == agj_sel].copy()

    # ----- 1. Kalkulimi i targetit dhe realizimit -----
    mask_ref = (df_tmp["data"].dt.date >= start_date) & (df_tmp["data"].dt.date <= end_date)
    df_agj_ref = df_tmp[mask_ref & (df_tmp["forcashitese"] == agj_sel)]
    n_months_ref = max(1, (end_date.year - start_date.year) * 12
                       + (end_date.month - start_date.month))

    kl_target = df_agj_ref.groupby("klienti")["kg"].sum().reset_index()
    kl_target["Target_Muaj"] = (kl_target["kg"] / n_months_ref) * (1 + rritja / 100)

    mask_live = (df_tmp["data"].dt.year == sot.year) & (df_tmp["data"].dt.month == sot.month)
    df_live_agj = df_tmp[mask_live & (df_tmp["forcashitese"] == agj_sel)]
    statusi_real = df_live_agj.groupby("klienti")["kg"].sum().reset_index()

    full_map = pd.merge(kl_target, statusi_real, on="klienti",
                        how="left", suffixes=("_target", "_real")).fillna(0)
    full_map["Ecuria"] = (full_map["kg_real"] / full_map["Target_Muaj"] * 100).replace([np.inf, -np.inf], 0)
    full_map["Mbetja_KG"] = (full_map["Target_Muaj"] - full_map["kg_real"]).clip(lower=0)

    # ----- 2. RFM Segmentimi (KJO është pjesa e "AI"-së reale) -----
    rfm = llogarit_rfm(df_tmp_agj, kolona_klienti="klienti")
    full_map = pd.merge(full_map, rfm[["klienti", "Segmenti", "RFM_Score", "R", "F", "M"]],
                        on="klienti", how="left")
    full_map["Segmenti"] = full_map["Segmenti"].fillna("Pak të dhëna")

    # ----- 3. Statistikat -----
    total_kliente = df_tmp_agj["klienti"].nunique()
    vizitat_count = df_live_agj.groupby("klienti")["data"].nunique().reset_index()
    double_visits = vizitat_count[vizitat_count["data"] > 1]["klienti"].tolist()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Klientë", total_kliente)
    c2.metric("Vizituar (Muaj)", len(statusi_real))
    c3.metric("Pa vizituar", total_kliente - len(statusi_real))
    c4.metric("Double Visits", len(double_visits),
              help="Klientë të faturuar më shumë se një herë brenda muajit.")

    # ----- 4. Grafiku i Segmenteve -----
    with st.expander("📊 Segmentimi RFM i Klientëve (KMeans-style)", expanded=False):
        st.markdown(
            "**Si lexohet:** RFM = Recency (kur ka blerë së fundi), "
            "Frequency (sa shpesh blen), Monetary (sa shumë blen). "
            "Algoritmi i grupon klientët automatikisht në segmente strategjike."
        )
        seg_count = rfm["Segmenti"].value_counts().reset_index()
        seg_count.columns = ["Segmenti", "Numri"]
        fig_seg = px.bar(seg_count, x="Segmenti", y="Numri",
                         color="Segmenti", text="Numri",
                         title=f"Shpërndarja e {len(rfm)} klientëve të {agj_sel}")
        fig_seg.update_traces(textposition="outside")
        st.plotly_chart(fig_seg, use_container_width=True)

    st.info(
        "ℹ️ **Mbetja në KG** = Target i Planit − Shitjet reale të muajit korrent. "
        "Kolona **Segmenti** vjen nga analiza RFM (më poshtë).",
        icon="💡"
    )

    tab1, tab2, tab3 = st.tabs([
        "🔴 Kritikë (60+ ditë)",
        "🟡 Prapa Planit",
        "🔵 Të Sugjeruar (Pa vizitë këtë muaj)",
    ])

    def mark_sot_ai(x):
        d = x.strftime("%d/%m/%Y")
        return f"⭐ {d} (SOT)" if d == data_sot_str else d

    # ----- TAB 1: Të humburit -----
    with tab1:
        kufiri_humbjes = sot - pd.Timedelta(days=60)
        blerja_f = df_tmp_agj.groupby("klienti")["data"].max().reset_index()
        kl_humbur = blerja_f[blerja_f["data"] < kufiri_humbjes].copy()
        kl_humbur["Blerja e Fundit"] = kl_humbur["data"].apply(mark_sot_ai)
        kl_humbur = kl_humbur.merge(rfm[["klienti", "Segmenti"]], on="klienti", how="left")
        kl_humbur["Vizito"] = False
        kl_humbur["Pezull"] = False
        ed_humb = st.data_editor(
            kl_humbur[["Vizito", "Pezull", "klienti", "Segmenti", "Blerja e Fundit"]],
            key="humb_v4", hide_index=True, use_container_width=True,
        )

    # ----- TAB 2: Rrezik plani -----
    with tab2:
        rrezik = (
            full_map[(full_map["Ecuria"] < 50) & (full_map["kg_real"] > 0)]
            .sort_values("Target_Muaj", ascending=False).copy()
        )
        rrezik["Vizito"] = False
        rrezik["Pezull"] = False
        ed_rrez = st.data_editor(
            rrezik[["Vizito", "Pezull", "klienti", "Segmenti", "Target_Muaj", "Ecuria"]],
            column_config={"Ecuria": st.column_config.NumberColumn(format="%.1f%%")},
            key="rrez_v4", hide_index=True, use_container_width=True,
        )

    # ----- TAB 3: Sugjerime -----
    with tab3:
        jo_vizituar = (
            full_map[full_map["kg_real"] == 0]
            .sort_values(["RFM_Score", "Target_Muaj"], ascending=[False, False]).copy()
        )
        jo_vizituar["Vizito"] = False
        jo_vizituar["Pezull"] = False
        ed_sugj = st.data_editor(
            jo_vizituar[["Vizito", "Pezull", "klienti", "Segmenti", "RFM_Score", "Target_Muaj"]],
            column_config={
                "Vizito": st.column_config.CheckboxColumn("Zgjidh"),
                "Pezull": st.column_config.CheckboxColumn("Pezull"),
                "Target_Muaj": st.column_config.NumberColumn("Objektivi KG"),
                "RFM_Score": st.column_config.NumberColumn(
                    "Skori AI", help="Sa më i lartë, aq më premtues klienti."
                ),
            },
            key="sugj_v5", hide_index=True, use_container_width=True,
        )

    # ----- 5. Procesimi i selektimeve (TANI VETËM NJË HERË — pa duplikat) -----
    s_h = ed_humb[(ed_humb["Vizito"] == True) & (ed_humb["Pezull"] == False)]["klienti"].tolist()
    s_r = ed_rrez[(ed_rrez["Vizito"] == True) & (ed_rrez["Pezull"] == False)]["klienti"].tolist()
    s_s = ed_sugj[(ed_sugj["Vizito"] == True) & (ed_sugj["Pezull"] == False)]["klienti"].tolist()
    lista_finale = sorted(set(s_h + s_r + s_s))

    st.divider()
    if not lista_finale:
        st.info("Zgjidhni klientët në tab-et e mësipërme për të gjeneruar planet.")
        return

    st.success(f"✅ Agjenda u krijua me {len(lista_finale)} klientë.")
    c_r1, c_r2, c_r3 = st.columns(3)

    if c_r1.button("📊 Raporti i Klientëve (KG & Vlera)"):
        cmimi_ref = 125
        rep_kl = full_map[full_map["klienti"].isin(lista_finale)].copy()
        rep_kl["Vlera"] = rep_kl["Mbetja_KG"] * cmimi_ref
        st.dataframe(rep_kl[["klienti", "Segmenti", "Mbetja_KG", "Vlera"]],
                     use_container_width=True)
        t_kg = rep_kl["Mbetja_KG"].sum()
        t_vl = rep_kl["Vlera"].sum()
        st.markdown(
            f"**TOTALI: {t_kg:,.1f} KG | {t_vl:,.1f} Lekë | "
            f"Çmimi Mes: {t_vl/t_kg if t_kg>0 else 0:,.1f} Lekë**"
        )

    if c_r2.button("📦 Raporti i Artikujve për Ngarkesë (Smart)"):
        # Sugjerim AI: artikujt që klienti blente shpesh por nuk po blen
        # tani — të peshuar me shpeshtësinë historike (jo thjesht binar).
        art_data = []
        kufiri_g = sot - pd.Timedelta(days=90)
        for k in lista_finale:
            mbetja_k = full_map[full_map["klienti"] == k]["Mbetja_KG"].values
            if len(mbetja_k) == 0:
                continue
            mbetja_k = float(mbetja_k[0])

            hist = df_tmp[(df_tmp["klienti"] == k) & (df_tmp["data"] < kufiri_g)]
            akt = df_tmp[(df_tmp["klienti"] == k) & (df_tmp["data"] >= kufiri_g)]
            if hist.empty:
                continue

            freq_hist = hist.groupby("artikulli")["data"].nunique()
            artikuj_aktiv = set(akt["artikulli"].unique())
            mungesa = freq_hist[~freq_hist.index.isin(artikuj_aktiv)]
            if mungesa.empty:
                art_data.append({"Artikulli": "PORTOFOL DIVERS", "Sasia KG": mbetja_k})
                continue

            # Peshojmë sipas shpeshtësisë — sa më shumë e ka blerë në të kaluarën,
            # aq më shumë KG i caktojmë tani (top 5 artikuj)
            top = mungesa.sort_values(ascending=False).head(5)
            shuma = top.sum()
            for art, freq in top.items():
                art_data.append({
                    "Artikulli": art,
                    "Sasia KG": mbetja_k * (freq / shuma) if shuma > 0 else 0,
                })

        if art_data:
            df_art = pd.DataFrame(art_data)
            raport = df_art.groupby("Artikulli")["Sasia KG"].sum().reset_index()
            raport = raport.sort_values("Sasia KG", ascending=False)
            st.dataframe(raport, use_container_width=True)
            st.markdown(f"**TOTALI: {raport['Sasia KG'].sum():,.1f} KG**")
        else:
            st.info("Nuk u gjetën artikuj specifikë.")

    if c_r3.button("🤖 Përmbledhje Strategjike (AI)"):
        with st.spinner("Po thërras LLM..."):
            konteksti = pergatit_kontekstin_per_llm(
                full_map, rfm,
                lista_humbur=kl_humbur["klienti"].tolist() if not kl_humbur.empty else [],
                vizitat_count=vizitat_count,
            )
            permbledhja = gjenero_permbledhje_llm(konteksti, agjenti=agj_sel)
        st.markdown("### 🤖 Plani i Sugjeruar nga AI")
        st.markdown(permbledhja)


# =========================================================
# MODULI 2: ROUTE PLAN AI (versioni i ri me OPTIMIZIM REAL)
# ---------------------------------------------------------
# NDRYSHIMI KRYESOR:
#   Versioni i vjetër thjesht shfaqte një hartë — nuk kishte
#   asnjë "optimizim itinerari" pavarësisht emrit.
#   Tani:
#   1) Llogarit rendin optimal të vizitave me Nearest-Neighbor.
#   2) Vizatojmë rrugën me numra mbi hartë (1→2→3→...).
#   3) Tregojmë distancën totale dhe distancën mes pikave.
#   4) Sugjerojmë pikën e nisjes (opsionale).
# =========================================================
def render_route_plan_ai(df_klientet_regjistri):
    st.title("🗺️ Route Plan AI — Optimizimi Real i Itinerareve")
    st.markdown(
        "Ky modul tani **e optimizon realisht** rendin e vizitave me algoritmin "
        "Nearest-Neighbor (TSP heuristik). Distancat janë në km (Haversine)."
    )

    if df_klientet_regjistri is None:
        st.error("❌ Nuk u ngarkuan të dhënat nga `KlientetListView`.")
        return

    df_aktiv = df_klientet_regjistri[df_klientet_regjistri["StatusiAktiv"] == True].copy()
    zonat = sorted(df_aktiv["ForcaShiteseAktuale"].dropna().unique())
    zona = st.selectbox("Zgjidh Agjentin / Zonën:", zonat)
    if not zona:
        return

    df_zona = df_aktiv[
        (df_aktiv["ForcaShiteseAktuale"] == zona)
        & (df_aktiv["Latitude"].notna())
        & (df_aktiv["Longitude"].notna())
    ].copy()
    df_zona.rename(columns={"Latitude": "latitude", "Longitude": "longitude"}, inplace=True)

    pa_geo = len(df_aktiv[df_aktiv["ForcaShiteseAktuale"] == zona]) - len(df_zona)
    c1, c2 = st.columns(2)
    c1.metric("🏪 Klientë Aktivë në Hartë", len(df_zona))
    c2.metric("📍 Pa Gjeolokacion", pa_geo,
              delta="- Jo në Hartë" if pa_geo > 0 else "Rregullt")

    if df_zona.empty:
        st.warning("⚠️ Asnjë klient i këtij agjenti nuk ka koordinata.")
        return

    # --- Konfigurimi i optimizimit ---
    with st.expander("⚙️ Konfigurimi i Rrugës", expanded=True):
        c1, c2, c3 = st.columns(3)
        nis_nga_qender = c1.checkbox("Fillo nga qendra gjeografike", value=True)
        max_klientesh = c2.slider("Maks. klientë në rrugë", 5, min(50, len(df_zona)),
                                  min(20, len(df_zona)))
        rendit_sipas = c3.selectbox("Prioritizo klientët sipas:",
                                    ["Të gjithë", "Më të afërt", "Sipas Rajonit"])

    # Marrim N klientët më të prioritarë (në këtë version: thjesht të parët)
    df_punes = df_zona.head(max_klientesh).copy() if rendit_sipas == "Të gjithë" else df_zona.copy()

    start_lat = df_punes["latitude"].mean() if nis_nga_qender else None
    start_lon = df_punes["longitude"].mean() if nis_nga_qender else None

    # --- Optimizimi ---
    df_opt = optimizo_rrugen_nn(
        df_punes[["KodiKlient", "Klienti", "Rajoni", "latitude", "longitude"]],
        start_lat=start_lat, start_lon=start_lon,
    )

    total_km = df_opt["Kumulative_km"].iloc[-1] if not df_opt.empty else 0
    st.success(f"✅ Rruga u optimizua: **{len(df_opt)} klientë**, "
               f"distancë totale **{total_km:.1f} km**")

    # --- Harta me rrugën e vizatuar ---
    st.subheader(f"🗺️ Itinerari Optimal: {zona}")
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=df_opt["latitude"], lon=df_opt["longitude"],
        mode="markers+lines+text",
        marker=dict(size=14, color="#1f77b4"),
        line=dict(width=2, color="rgba(31,119,180,0.6)"),
        text=df_opt["Rendi"].astype(str),
        textposition="top center",
        hovertext=df_opt["Klienti"] + " (Stop #" + df_opt["Rendi"].astype(str) + ")",
        hoverinfo="text",
        name="Rruga"
    ))
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=11,
        mapbox_center={"lat": df_opt["latitude"].mean(),
                       "lon": df_opt["longitude"].mean()},
        height=600,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Tabela e renditur ---
    st.subheader("📋 Rendi i Vizitave")
    st.dataframe(
        df_opt[["Rendi", "KodiKlient", "Klienti", "Rajoni", "Distanca_km", "Kumulative_km"]],
        column_config={
            "Rendi": st.column_config.NumberColumn("#", width="small"),
            "Distanca_km": st.column_config.NumberColumn("Dist. nga më parë (km)", format="%.2f"),
            "Kumulative_km": st.column_config.NumberColumn("Kumulative (km)", format="%.2f"),
        },
        use_container_width=True, hide_index=True,
    )

    csv = df_opt.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Shkarko Rrugën Optimale (CSV)",
                       csv, f"rruga_optimale_{zona}.csv", "text/csv",
                       use_container_width=True)


# =========================================================
# MODULI 3: ROUTE PLAN AI-2 (me Churn Score)
# ---------------------------------------------------------
# NDRYSHIMI:
#   Versioni i vjetër ndante klientët në "aktivë / të humbur"
#   thjesht me një kufi date (01/01 i vitit të kaluar).
#   Tani shtohet një SKOR CHURN nga 0-100 për çdo klient,
#   bazuar mbi: ditë pa blerë, frekuenca historike, vlera mesatare.
# =========================================================
def render_route_plan_ai_2(df_raw):
    st.title("🎯 Analiza e Agjentëve & Klientëve me Churn Score")

    if df_raw is None or df_raw.empty:
        st.error("⚠️ Nuk u gjetën të dhëna.")
        return

    sot = datetime.now()
    viti_aktual = sot.year
    muaji_aktual = sot.month
    if muaji_aktual == 1:
        muaji_kaluar, viti_muajit_kaluar = 12, viti_aktual - 1
    else:
        muaji_kaluar, viti_muajit_kaluar = muaji_aktual - 1, viti_aktual
    data_limit_humbur = datetime(viti_aktual - 1, 1, 1)

    st.info(
        f"📅 Muaji i fundit i plotë: **{muaji_kaluar}/{viti_muajit_kaluar}**. "
        f"Klientët e humbur: pa blerje që nga **01/01/{viti_aktual - 1}**."
    )

    df_k = df_raw.copy()
    df_k["Viti"] = df_k["Data"].dt.year
    df_k["Muaji"] = df_k["Data"].dt.month
    mask_muaji = (df_k["Viti"] == viti_muajit_kaluar) & (df_k["Muaji"] == muaji_kaluar)
    agjentet_aktive = df_k[mask_muaji]["ForcaShitese"].unique()
    df_f = df_k[df_k["ForcaShitese"].isin(agjentet_aktive)].copy()

    klient_status = (
        df_f.groupby(["ForcaShitese", "KodiKlient", "Klienti"])
        .agg(
            Data_Blerjes_Fundit=("Data", "max"),
            Totale_KG=("kg", "sum"),
            Totale_Vlera=("Vlera_Historike", "sum"),
            Numri_Blerjeve=("Data", "nunique"),
        ).reset_index()
    )
    klient_status["Ditë_pa_Blerë"] = (sot - klient_status["Data_Blerjes_Fundit"]).dt.days

    # ----- CHURN SCORE 0-100 -----
    # Logjika: pesha 60% recency + 25% frekuencë + 15% vlerë e ulët
    dpb = klient_status["Ditë_pa_Blerë"]
    klient_status["Skor_Recency"] = np.clip(dpb / dpb.quantile(0.95) * 100, 0, 100)
    klient_status["Skor_Freq"] = 100 - np.clip(
        klient_status["Numri_Blerjeve"]
        / klient_status["Numri_Blerjeve"].quantile(0.95) * 100, 0, 100
    )
    klient_status["Skor_Vlere"] = 100 - np.clip(
        klient_status["Totale_Vlera"]
        / klient_status["Totale_Vlera"].quantile(0.95) * 100, 0, 100
    )
    klient_status["Churn_Score"] = (
        0.60 * klient_status["Skor_Recency"]
        + 0.25 * klient_status["Skor_Freq"]
        + 0.15 * klient_status["Skor_Vlere"]
    ).round(0).astype(int)

    def kategori_churn(s):
        if s >= 75: return "🔴 I Humbur"
        if s >= 50: return "🟠 Rrezik i Lartë"
        if s >= 30: return "🟡 Vëzhgim"
        return "🟢 Stabël"

    klient_status["Statusi"] = klient_status["Churn_Score"].apply(kategori_churn)

    mask_humbur = klient_status["Data_Blerjes_Fundit"] < data_limit_humbur
    df_humbur = klient_status[mask_humbur].copy()
    df_aktive = klient_status[~mask_humbur].copy()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Agjentë Aktivë", len(agjentet_aktive))
    m2.metric("Klientë Aktivë", len(df_aktive))
    m3.metric("Klientë të Humbur", len(df_humbur))
    rrezik_l = len(df_aktive[df_aktive["Churn_Score"] >= 50])
    m4.metric("🟠 Në Rrezik (aktivë)", rrezik_l,
              help="Klientë ende aktivë por me Churn Score ≥ 50")

    st.divider()

    tab_aktive, tab_rrezik, tab_humbur = st.tabs([
        "📍 Rrugët Operative",
        "⚠️ Klientët në Rrezik",
        "🛑 Të Humbur",
    ])

    with tab_aktive:
        agj_zgj = st.selectbox("Zgjidh Agjentin:", sorted(list(agjentet_aktive)),
                               key="rp2_agj")
        df_rr = df_aktive[df_aktive["ForcaShitese"] == agj_zgj].sort_values(
            "Churn_Score", ascending=False
        )
        st.markdown(f"**Klientët e `{agj_zgj}` (renditur sipas Churn Score):**")
        st.dataframe(
            df_rr[["KodiKlient", "Klienti", "Statusi", "Churn_Score",
                   "Data_Blerjes_Fundit", "Ditë_pa_Blerë", "Totale_KG"]],
            column_config={
                "Churn_Score": st.column_config.ProgressColumn(
                    "Churn", format="%d", min_value=0, max_value=100
                ),
            },
            use_container_width=True, hide_index=True,
        )
        st.download_button("📥 Shkarko (CSV)",
                           df_rr.to_csv(index=False).encode("utf-8"),
                           f"rruga_{agj_zgj}.csv", "text/csv",
                           use_container_width=True)

    with tab_rrezik:
        st.subheader("⚠️ Klientë Aktivë por në Rrezik (Churn ≥ 50)")
        df_rr = df_aktive[df_aktive["Churn_Score"] >= 50].sort_values(
            "Churn_Score", ascending=False
        )
        st.dataframe(
            df_rr[["ForcaShitese", "KodiKlient", "Klienti", "Statusi",
                   "Churn_Score", "Ditë_pa_Blerë", "Totale_Vlera"]],
            column_config={
                "Churn_Score": st.column_config.ProgressColumn(
                    "Churn", min_value=0, max_value=100
                ),
            },
            use_container_width=True, hide_index=True,
        )

    with tab_humbur:
        st.warning("⚠️ Këta klientë janë jashtë rrugëve operative — vetëm për fushata rikthimi.")
        st.dataframe(
            df_humbur[["ForcaShitese", "KodiKlient", "Klienti",
                       "Data_Blerjes_Fundit", "Ditë_pa_Blerë",
                       "Totale_Vlera", "Churn_Score"]].sort_values(
                "Ditë_pa_Blerë", ascending=False
            ),
            use_container_width=True, hide_index=True,
        )
        st.download_button("📥 Shkarko të Humburit (CSV)",
                           df_humbur.to_csv(index=False).encode("utf-8"),
                           "klientet_e_humbur.csv", "text/csv",
                           use_container_width=True)


# =========================================================
# SI TA INTEGROSH NË app.py
# ---------------------------------------------------------
# 1) Vendos këtë skedar afër app.py.
# 2) Në krye të app.py shto:
#      from ai_modules_improved import (
#          render_asistenti_ai,
#          render_route_plan_ai,
#          render_route_plan_ai_2,
#      )
# 3) Zëvendëso blloqet ekzistuese me thirrjet përkatëse:
#
#      elif page == "Asistenti AI":
#          render_asistenti_ai(df_raw, agj_sel, start_date, end_date, rritja)
#
#      elif page == "Route Plan AI":
#          render_route_plan_ai(df_klientet_regjistri)
#
#      elif page == "Route Plan AI-2":
#          render_route_plan_ai_2(df_raw)
#
# 4) Shto në requirements.txt:
#      scikit-learn   # opsionale; kodi punon edhe pa, por për versionet
#                       që zgjasin RFM-në me KMeans real do duhet.
# =========================================================
