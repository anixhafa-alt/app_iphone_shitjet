# =========================================================
# AXION - Modulet AI (v3.1 — i pastruar dhe me Gemini)
# =========================================================
# Eksporton: render_plan_ditor (moduli kryesor i unifikuar)
#
# Provider-at e mbeshtetur per LLM (zgjidh ne secrets.toml):
#   LLM_PROVIDER = "anthropic"  -> ANTHROPIC_API_KEY
#   LLM_PROVIDER = "openai"     -> OPENAI_API_KEY
#   LLM_PROVIDER = "gemini"     -> GEMINI_API_KEY
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import json
import os


# =========================================================
# HELPER-AT E VEGJEL
# =========================================================
def _safe_int(val, default=0):
    try:
        if pd.isna(val):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


# =========================================================
# LLM: Claude / OpenAI / Gemini
# =========================================================
def _merr_konfigurimin_llm():
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
            api_key = ""
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", "")
        except Exception:
            api_key = ""
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    elif provider == "gemini":
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            api_key = ""
        api_key = api_key or os.getenv("GEMINI_API_KEY", "")
    return provider, api_key


def gjenero_permbledhje_llm(konteksti, agjenti):
    provider, api_key = _merr_konfigurimin_llm()
    if not provider or not api_key:
        return (
            "LLM nuk eshte konfiguruar. Shto ne `.streamlit/secrets.toml`:\n\n"
            "```toml\n"
            'LLM_PROVIDER = "gemini"\n'
            'GEMINI_API_KEY = "..."\n'
            "```\n"
            "Provider-at e mbeshtetur: anthropic, openai, gemini."
        )

    prompt_sistemi = (
        "Je nje konsulent shitjesh qe ndihmon menaxheret e shitjeve ne Shqiperi. "
        "Pergjigju gjithmone ne shqip. Jep keshilla konkrete, jo gjenerale. "
        "Strukturo si: (1) Diagnoza, (2) 3 Prioritetet, (3) Klientet kyc per t'u kontaktuar. "
        "Mos shpik te dhena qe s'jane ne kontekst. Maks. 250 fjale."
    )
    prompt_perdoruesi = (
        "Te dhenat per agjentin " + str(agjenti) + ":\n\n"
        "```json\n" + json.dumps(konteksti, ensure_ascii=False, indent=2) + "\n```\n\n"
        "Hartoji nje plan strategjik per kete dite."
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

        elif provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=prompt_sistemi,
            )
            resp = model.generate_content(prompt_perdoruesi)
            return resp.text

        else:
            return "Provider i panjohur: " + str(provider)

    except ImportError as e:
        paketa = {"anthropic": "anthropic", "openai": "openai",
                  "gemini": "google-generativeai"}.get(provider, "?")
        return "Paketa mungon. Instalo: pip install " + paketa + "\n\nDetaji: " + str(e)
    except Exception as e:
        return "Gabim gjate thirrjes se LLM: " + str(e)


# =========================================================
# RFM SEGMENTIMI
# =========================================================
@st.cache_data(ttl=600, show_spinner=False)
def llogarit_rfm(df, kolona_klienti="klienti"):
    if df.empty:
        return pd.DataFrame()
    sot = pd.Timestamp(datetime.now().date())
    d = df.copy()
    d["data"] = pd.to_datetime(d["data"], errors="coerce")
    d = d.dropna(subset=["data"])

    rfm = d.groupby(kolona_klienti).agg(
        R=("data", lambda x: (sot - x.max()).days),
        F=("data", "nunique"),
        M=("kg", "sum"),
    ).reset_index()

    if len(rfm) < 4:
        rfm["RFM_Score"] = 0
        rfm["Segmenti"] = "Pak te dhena"
        return rfm

    try:
        rfm["R_Skor"] = pd.qcut(rfm["R"], q=min(5, rfm["R"].nunique()),
                                labels=False, duplicates="drop") + 1
        rfm["R_Skor"] = 6 - rfm["R_Skor"]
        rfm["F_Skor"] = pd.qcut(rfm["F"].rank(method="first"),
                                q=min(5, rfm["F"].nunique()),
                                labels=False, duplicates="drop") + 1
        rfm["M_Skor"] = pd.qcut(rfm["M"].rank(method="first"),
                                q=min(5, rfm["M"].nunique()),
                                labels=False, duplicates="drop") + 1
    except Exception:
        rfm["R_Skor"] = 3
        rfm["F_Skor"] = 3
        rfm["M_Skor"] = 3

    rfm["R_Skor"] = rfm["R_Skor"].fillna(3).astype(int)
    rfm["F_Skor"] = rfm["F_Skor"].fillna(3).astype(int)
    rfm["M_Skor"] = rfm["M_Skor"].fillna(3).astype(int)
    rfm["RFM_Score"] = rfm["R_Skor"] + rfm["F_Skor"] + rfm["M_Skor"]

    def kategorizo(row):
        r = row["R_Skor"]
        f = row["F_Skor"]
        m = row["M_Skor"]
        if r >= 4 and f >= 4 and m >= 4:
            return "Kampionet"
        if r >= 4 and f >= 3:
            return "Besnike"
        if r >= 4 and f <= 2:
            return "Te Rinj"
        if r <= 2 and f >= 4 and m >= 4:
            return "Ne Rrezik (VIP)"
        if r <= 2 and f >= 3:
            return "Po humbasin"
        if r <= 2 and f <= 2:
            return "Te Humbur"
        return "Standard"

    rfm["Segmenti"] = rfm.apply(kategorizo, axis=1)
    return rfm


# =========================================================
# OPTIMIZIMI I RRUGES (Nearest-Neighbor TSP)
# =========================================================
def distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def optimizo_rrugen_nn(df_pikat, start_lat=None, start_lon=None):
    if df_pikat.empty:
        return df_pikat

    pts = df_pikat.reset_index(drop=True).copy()
    n = len(pts)
    visited = [False] * n
    order = []

    if start_lat is None or start_lon is None:
        start_idx = 0
    else:
        d = distance_km(start_lat, start_lon,
                        pts["latitude"].values, pts["longitude"].values)
        start_idx = int(np.argmin(d))

    order.append(start_idx)
    visited[start_idx] = True
    last_lat = pts.loc[start_idx, "latitude"]
    last_lon = pts.loc[start_idx, "longitude"]
    distances = [0.0]

    while len(order) < n:
        d = distance_km(last_lat, last_lon,
                        pts["latitude"].values, pts["longitude"].values)
        mask = np.array(visited)
        d_arr = np.where(mask, np.inf, d)
        nxt = int(np.argmin(d_arr))
        order.append(nxt)
        visited[nxt] = True
        distances.append(float(d_arr[nxt]))
        last_lat = pts.loc[nxt, "latitude"]
        last_lon = pts.loc[nxt, "longitude"]

    rezultati = pts.iloc[order].reset_index(drop=True)
    rezultati["Rendi"] = range(1, len(rezultati) + 1)
    rezultati["Distanca_km"] = distances
    rezultati["Kumulative_km"] = np.cumsum(distances)
    return rezultati


# =========================================================
# PRIORITY SCORE
# =========================================================
def _llogarit_priority_score(full_map, rfm, df_agj, sot):
    df = full_map.copy()

    blerja_fundit = df_agj.groupby("klienti")["data"].max().reset_index()
    blerja_fundit["dite_pa_blere"] = (sot - blerja_fundit["data"]).dt.days
    df = df.merge(blerja_fundit[["klienti", "dite_pa_blere"]], on="klienti", how="left")
    df["dite_pa_blere"] = df["dite_pa_blere"].fillna(999).astype(int)

    df["k_ecuria"] = (100 - df["Ecuria"].fillna(0).clip(0, 100)).clip(0, 100)
    df["k_recency"] = (df["dite_pa_blere"] / 60 * 100).clip(0, 100)

    seg_bonus = {
        "Ne Rrezik (VIP)": 100,
        "Po humbasin": 85,
        "Kampionet": 70,
        "Besnike": 55,
        "Te Humbur": 60,
        "Standard": 40,
        "Te Rinj": 30,
        "Pak te dhena": 20,
    }
    df["k_segment"] = df["Segmenti"].map(seg_bonus).fillna(40)

    mbetja_max = df["Mbetja_KG"].fillna(0).quantile(0.95)
    if mbetja_max and mbetja_max > 0:
        df["k_mbetja"] = (df["Mbetja_KG"].fillna(0) / mbetja_max * 100).clip(0, 100)
    else:
        df["k_mbetja"] = 0

    df["Priority_Score"] = (
        0.30 * df["k_ecuria"].fillna(0)
        + 0.30 * df["k_recency"].fillna(0)
        + 0.20 * df["k_segment"].fillna(40)
        + 0.20 * df["k_mbetja"].fillna(0)
    ).fillna(0).round(0).astype(int)

    return df.drop(columns=["k_ecuria", "k_recency", "k_segment", "k_mbetja"])


# =========================================================
# SUGJERIMET E PRODUKTEVE (Gap analysis i peshuar)
# =========================================================
def _sugjero_produkte(df_full, klienti, mbetja_kg, sot, top_n=3):
    kufiri = sot - pd.Timedelta(days=90)
    df_k = df_full[df_full["klienti"] == klienti]
    if df_k.empty:
        return []

    hist = df_k[df_k["data"] < kufiri]
    akt = df_k[df_k["data"] >= kufiri]
    sugjerime = []

    if not hist.empty:
        freq = hist.groupby("artikulli")["data"].nunique()
        artikuj_akt = set(akt["artikulli"].unique())
        mungesa = freq[~freq.index.isin(artikuj_akt)].sort_values(ascending=False)
        if not mungesa.empty:
            top = mungesa.head(top_n)
            shuma = top.sum()
            for art, fr in top.items():
                sasia = mbetja_kg * (fr / shuma) if shuma > 0 else 0
                sugjerime.append({
                    "artikulli": str(art)[:40],
                    "sasia_kg": round(float(sasia), 1),
                    "arsyeja": "Gap (90 dite)",
                })

    if not sugjerime and not df_k.empty:
        top_sellers = df_k.groupby("artikulli")["kg"].sum().sort_values(ascending=False).head(top_n)
        shuma = top_sellers.sum()
        for art, kg in top_sellers.items():
            sasia = mbetja_kg * (kg / shuma) if shuma > 0 else 0
            sugjerime.append({
                "artikulli": str(art)[:40],
                "sasia_kg": round(float(sasia), 1),
                "arsyeja": "Top seller historik",
            })

    return sugjerime


# =========================================================
# MODULI KRYESOR: PLANI DITOR I AGJENTIT
# =========================================================
def render_plan_ditor(df_raw, df_klientet_regjistri, agj_sel,
                       start_date, end_date, rritja):
    st.title("Plani Ditor i Agjentit")
    st.markdown(
        "Ky modul bashkon prioritizimin, optimizimin e rruges dhe sugjerimet "
        "e produkteve ne nje rrjedhe te vetme."
    )

    if agj_sel == "Te gjithe":
        st.warning("Zgjidh nje agjent specifik ne sidebar.")
        return

    if df_raw is None or df_raw.empty:
        st.error("Nuk u gjeten te dhena.")
        return

    # 1. Konfigurimi
    col1, col2, col3 = st.columns([1, 1, 2])
    maks_vizita = col1.slider("Maks. vizita / dite", 10, 25, 18)
    data_plani = col2.date_input("Data e planit", value=datetime.now().date())
    treg_konflikte = col3.checkbox(
        "Shfaq flag-un e konfliktit (agjente te ndare)", value=True,
    )

    # 2. Pergatitja
    sot = pd.Timestamp(data_plani)
    df = df_raw.copy()
    df.columns = [c.lower() for c in df.columns]
    df_agj = df[df["forcashitese"] == agj_sel].copy()
    if df_agj.empty:
        st.warning("Asnje e dhene per agjentin " + str(agj_sel) + ".")
        return

    # 3. Target dhe realizimi
    mask_ref = (df["data"].dt.date >= start_date) & (df["data"].dt.date <= end_date)
    df_ref = df[mask_ref & (df["forcashitese"] == agj_sel)]
    n_months = max(1, (end_date.year - start_date.year) * 12
                   + (end_date.month - start_date.month))
    kl_target = df_ref.groupby("klienti")["kg"].sum().reset_index()
    kl_target["Target_Muaj"] = (kl_target["kg"] / n_months) * (1 + rritja / 100)

    mask_live = (df["data"].dt.year == sot.year) & (df["data"].dt.month == sot.month)
    df_live = df[mask_live & (df["forcashitese"] == agj_sel)]
    statusi_real = df_live.groupby("klienti")["kg"].sum().reset_index()

    full_map = pd.merge(kl_target, statusi_real, on="klienti",
                        how="left", suffixes=("_target", "_real")).fillna(0)
    full_map["Ecuria"] = (
        (full_map["kg_real"] / full_map["Target_Muaj"] * 100)
        .replace([np.inf, -np.inf], 0)
        .fillna(0)
    )
    full_map["Mbetja_KG"] = (full_map["Target_Muaj"] - full_map["kg_real"]).clip(lower=0).fillna(0)

    # 4. RFM
    rfm = llogarit_rfm(df_agj, kolona_klienti="klienti")
    if not rfm.empty:
        full_map = full_map.merge(rfm[["klienti", "Segmenti", "RFM_Score"]],
                                  on="klienti", how="left")
    else:
        full_map["Segmenti"] = "Pak te dhena"
        full_map["RFM_Score"] = 0
    full_map["Segmenti"] = full_map["Segmenti"].fillna("Pak te dhena")
    full_map["RFM_Score"] = full_map["RFM_Score"].fillna(0)

    # 5. Konfliktet
    konflikti = df_ref.groupby("klienti")["forcashitese"].nunique().reset_index()
    konflikti["ka_konflikt"] = konflikti["forcashitese"] > 1
    full_map = full_map.merge(konflikti[["klienti", "ka_konflikt"]],
                              on="klienti", how="left")
    full_map["ka_konflikt"] = full_map["ka_konflikt"].fillna(False)

    # 6. Priority Score
    full_map = _llogarit_priority_score(full_map, rfm, df_agj, sot)

    # 7. Koordinatat
    if df_klientet_regjistri is not None and not df_klientet_regjistri.empty:
        reg = df_klientet_regjistri[["Klienti", "Latitude", "Longitude", "Rajoni"]].copy()
        reg.columns = ["klienti", "latitude", "longitude", "rajoni"]
        reg["klienti_k"] = reg["klienti"].astype(str).str.strip().str.upper()
        full_map["klienti_k"] = full_map["klienti"].astype(str).str.strip().str.upper()
        full_map = full_map.merge(
            reg[["klienti_k", "latitude", "longitude", "rajoni"]],
            on="klienti_k", how="left"
        ).drop(columns=["klienti_k"])
    else:
        full_map["latitude"] = np.nan
        full_map["longitude"] = np.nan
        full_map["rajoni"] = ""

    # 8. Top N
    kandidatet = full_map.sort_values("Priority_Score", ascending=False).head(maks_vizita).copy()
    kandidatet_me_geo = kandidatet.dropna(subset=["latitude", "longitude"]).copy()

    # 9. Metrikat
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Klientet ne Plan", len(kandidatet))
    m2.metric("Target KG i Mbetjes", "{:,.0f}".format(kandidatet["Mbetja_KG"].sum()))
    konfl_n = int(kandidatet["ka_konflikt"].sum())
    m3.metric("Konflikte", konfl_n)
    pa_geo = len(kandidatet) - len(kandidatet_me_geo)
    m4.metric("Pa Gjeolokacion", pa_geo)
    st.divider()

    # 10. Optimizimi
    df_opt = pd.DataFrame()
    if not kandidatet_me_geo.empty:
        kolonat = ["klienti", "rajoni", "latitude", "longitude",
                   "Priority_Score", "Mbetja_KG", "Segmenti",
                   "ka_konflikt", "Target_Muaj", "Ecuria"]
        df_opt = optimizo_rrugen_nn(
            kandidatet_me_geo[kolonat],
            start_lat=None, start_lon=None,
        )
        total_km = df_opt["Kumulative_km"].iloc[-1] if not df_opt.empty else 0
        st.success(
            "Plani u krijua: {} klientet, {:,.0f} kg per te shitur, distance {:.1f} km".format(
                len(df_opt), df_opt["Mbetja_KG"].sum(), total_km
            )
        )

        # 11. Harta
        st.subheader("Itinerari Optimal i Dites")
        fig = go.Figure()
        for ka_konfl, ngjyra, emri in [(True, "#d32f2f", "Konflikt"),
                                        (False, "#1f77b4", "Normal")]:
            df_m = df_opt[df_opt["ka_konflikt"] == ka_konfl]
            if df_m.empty:
                continue
            fig.add_trace(go.Scattermapbox(
                lat=df_m["latitude"], lon=df_m["longitude"],
                mode="markers+text",
                marker=dict(size=16, color=ngjyra),
                text=df_m["Rendi"].astype(str),
                textposition="top center",
                hovertext=df_m["klienti"].astype(str),
                hoverinfo="text",
                name=emri if treg_konflikte else "Pikat",
                showlegend=treg_konflikte,
            ))
        fig.add_trace(go.Scattermapbox(
            lat=df_opt["latitude"], lon=df_opt["longitude"],
            mode="lines",
            line=dict(width=2, color="rgba(31,119,180,0.5)"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox_zoom=11,
            mapbox_center=dict(
                lat=float(df_opt["latitude"].mean()),
                lon=float(df_opt["longitude"].mean()),
            ),
            height=550,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Asnje klient ne plan nuk ka koordinata.")

    # 12. Tabela e plote me produkte
    st.subheader("Plani i Vizitave + Produktet per Oferte")
    plan_rrjeshtor = []
    if not df_opt.empty:
        rendor_iter = df_opt.iterrows()
    else:
        kand_temp = kandidatet.copy()
        kand_temp["Rendi"] = range(1, len(kand_temp) + 1)
        rendor_iter = kand_temp.iterrows()

    for _, rresht in rendor_iter:
        klienti = rresht["klienti"]
        mbetja = _safe_float(rresht.get("Mbetja_KG", 0))
        sugj = _sugjero_produkte(df, klienti, mbetja, sot, top_n=3)
        if sugj:
            produktet_tekst = " | ".join(
                ["{} ({:.0f}kg)".format(s["artikulli"], s["sasia_kg"]) for s in sugj]
            )
        else:
            produktet_tekst = "-"

        segm = rresht.get("Segmenti", "")
        if pd.isna(segm):
            segm = ""

        konfl_val = rresht.get("ka_konflikt", False)
        konfl_str = "Konflikt" if konfl_val else ""

        plan_rrjeshtor.append({
            "Rendi": _safe_int(rresht.get("Rendi", 0)),
            "Klienti": klienti,
            "Priority": _safe_int(rresht.get("Priority_Score", 0)),
            "Segment": segm,
            "Konflikt": konfl_str,
            "Mbetja_KG": round(mbetja, 1),
            "Distanca_km": round(_safe_float(rresht.get("Distanca_km", 0)), 2),
            "Produktet": produktet_tekst,
        })

    df_plan = pd.DataFrame(plan_rrjeshtor)
    st.dataframe(df_plan, use_container_width=True, hide_index=True)

    # 13. Eksporti
    col_e1, col_e2, col_e3 = st.columns(3)
    csv_data = df_plan.to_csv(index=False).encode("utf-8-sig")
    col_e1.download_button(
        "Shkarko CSV",
        csv_data,
        "plan_ditor_" + str(agj_sel) + "_" + data_plani.strftime("%Y%m%d") + ".csv",
        "text/csv",
        use_container_width=True,
    )

    detaj_rrjeshta = []
    for p in plan_rrjeshtor:
        sugj = _sugjero_produkte(df, p["Klienti"], p["Mbetja_KG"], sot, top_n=3)
        if sugj:
            for s in sugj:
                detaj_rrjeshta.append({
                    "Rendi": p["Rendi"],
                    "Klienti": p["Klienti"],
                    "Artikulli": s["artikulli"],
                    "Sasia_KG": s["sasia_kg"],
                    "Arsyeja": s["arsyeja"],
                })
        else:
            detaj_rrjeshta.append({
                "Rendi": p["Rendi"], "Klienti": p["Klienti"],
                "Artikulli": "-", "Sasia_KG": 0, "Arsyeja": "Pa sugjerim",
            })

    csv_detaj = pd.DataFrame(detaj_rrjeshta).to_csv(index=False).encode("utf-8-sig")
    col_e2.download_button(
        "Shkarko Detaj (CSV)",
        csv_detaj,
        "plan_detaj_" + str(agj_sel) + "_" + data_plani.strftime("%Y%m%d") + ".csv",
        "text/csv",
        use_container_width=True,
    )

    # 14. LLM
    if col_e3.button("Permbledhje AI", use_container_width=True):
        with st.spinner("Po therras LLM..."):
            kontekst_llm = {
                "agjenti": str(agj_sel),
                "data_plani": data_plani.strftime("%d/%m/%Y"),
                "klientet_ne_plan": len(df_plan),
                "target_kg_per_dite": float(df_plan["Mbetja_KG"].sum()),
                "distanca_km": float(df_opt["Kumulative_km"].iloc[-1]) if not df_opt.empty else 0,
                "klientet_me_konflikt": int((df_plan["Konflikt"] == "Konflikt").sum()),
                "top_5_klientet": df_plan.head(5)[
                    ["Klienti", "Priority", "Segment", "Mbetja_KG", "Produktet"]
                ].to_dict(orient="records"),
            }
            permbledhja = gjenero_permbledhje_llm(kontekst_llm, agjenti=agj_sel)
        st.markdown("### Permbledhje Strategjike")
        st.markdown(permbledhja)
