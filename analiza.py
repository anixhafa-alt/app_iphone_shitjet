import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render_analiza_klienteve(df_raw):
    st.title("📊 Analiza e Mundësive dhe Rrezikut të Klientëve")
    st.markdown(
        "Identifikimi i klientëve të fjetur, në rrezik dhe atyre stabil bazuar në historikun e shitjeve nga databaza."
    )

    if df_raw is None or df_raw.empty:
        st.warning("⚠️ Nuk ka të dhëna të ngarkuara nga skedari SAD-DATAbase1.xlsb.")
        return

    # --- PASTRIMI DHE FORMATIMI I TË DHËNAVE ---
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.replace('"', "")

    # Konvertimi i Datës në mënyrë të sigurt
    if pd.api.types.is_numeric_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(
            df["Data"], unit="D", origin="1899-12-30"
        ).dt.normalize()
    else:
        df["Data"] = pd.to_datetime(
            df["Data"], dayfirst=True, errors="coerce"
        ).dt.normalize()

    # Filtro vetëm 3 vitet e fundit (Viti aktual 2026)
    current_year = 2026
    start_date_analysis = datetime(current_year - 3, 1, 1)
    df = df[df["Data"] >= start_date_analysis]

    # Konvertimi i kolonave numerike kritike
    for col in ["TotalRresht", "kg"]:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace(",", "", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0.0

    # Mbajmë vetëm transaksionet pozitive
    df = df[df["TotalRresht"] > 0]

    if df.empty:
        st.error("❌ Nuk ka transaksione valide (me vlerë mbi 0) pas filtrimit.")
        return

    # --- LOGJIKA E PROCESIMIT (Analiza jote origjinale) ---
    max_date = df["Data"].max()

    # Agregimi sipas Agjentit (ForcaShitese) dhe Klientit
    client_stats = (
        df.groupby(["ForcaShitese", "Klienti"])
        .agg(
            Last_Date=("Data", "max"),
            First_Date=("Data", "min"),
            Total_Sales=("TotalRresht", "sum"),
            Sales_Count=("TotalRresht", "count"),
        )
        .reset_index()
    )

    client_stats["Days_Inactive"] = (max_date - client_stats["Last_Date"]).dt.days
    client_stats["Months_Active"] = (
        (client_stats["Last_Date"] - client_stats["First_Date"]).dt.days / 30
    ).astype(int)
    client_stats["Months_Active"] = client_stats["Months_Active"].replace(0, 1)
    client_stats["Avg_Monthly"] = (
        client_stats["Total_Sales"] / client_stats["Months_Active"]
    )

    # 1. Klientët e Fjetur
    churn_clients = client_stats[
        (client_stats["Days_Inactive"] > 60) & (client_stats["Total_Sales"] > 50000)
    ].copy()
    churn_clients["Status"] = "Fjetur"

    # 2. Klientët në Rrezik Rënieje (90 ditët e fundit)
    last_90_days = max_date - timedelta(days=90)
    recent_sales = (
        df[df["Data"] >= last_90_days]
        .groupby(["ForcaShitese", "Klienti"])["TotalRresht"]
        .sum()
        .reset_index()
    )
    recent_sales.rename(columns={"TotalRresht": "Recent_Sales"}, inplace=True)

    risk_analysis = pd.merge(
        client_stats, recent_sales, on=["ForcaShitese", "Klienti"], how="left"
    ).fillna(0)
    risk_clients = risk_analysis[
        (risk_analysis["Days_Inactive"] <= 45)
        & (risk_analysis["Recent_Sales"] < (risk_analysis["Avg_Monthly"] * 3 * 0.6))
        & (risk_analysis["Avg_Monthly"] > 5000)
    ].copy()
    risk_clients["Status"] = "Rrezik"

    # 3. Klientët Stabilë
    all_analyzed = pd.concat([churn_clients, risk_clients])
    stable_clients = client_stats[
        ~client_stats["Klienti"].isin(all_analyzed["Klienti"])
    ].copy()
    stable_clients["Status"] = "Stabil"

    # --- RENDITJA ---
    churn_clients = churn_clients.sort_values(by="Total_Sales", ascending=False)
    risk_clients = risk_clients.sort_values(by="Avg_Monthly", ascending=False)
    stable_clients = stable_clients.sort_values(by="Total_Sales", ascending=False)

    # --- NDËRFAQJA GRAFIKE (TABS) ---
    tab1, tab2, tab3 = st.tabs(
        ["🔴 Ri-aktivizim (Fjetur)", "🟡 Në Rrezik (Rënie)", "🟢 Klientë Stabilë"]
    )

    with tab1:
        st.subheader(f"Klientët e Fjetur ({len(churn_clients)})")
        st.info(
            "💡 Klientë me blerje historike të larta (>50k Lek), por që nuk kanë blerë asgjë në 60 ditët e fundit."
        )
        if not churn_clients.empty:
            # Formatimi i kolonës së parave për shfaqje më të bukur
            churn_display = churn_clients[
                ["ForcaShitese", "Klienti", "Days_Inactive", "Total_Sales"]
            ].copy()
            churn_display["Total_Sales"] = churn_display["Total_Sales"].map(
                "{:,.2f} Lek".format
            )

            st.dataframe(
                churn_display.rename(
                    columns={
                        "ForcaShitese": "Agjenti",
                        "Days_Inactive": "Ditë pa Blerë",
                        "Total_Sales": "Totali Historik",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.success("✅ Shkëlqyeshëm! Nuk ka klientë të fjetur.")

    with tab2:
        st.subheader(f"Klientët në Rrezik Rënieje ({len(risk_clients)})")
        st.warning(
            "⚠️ Klientë aktivë, por që xhiroja e tyre në 90 ditët e fundit ka rënë nën 60% të mesatares së tyre normale."
        )
        if not risk_clients.empty:
            risk_display = risk_clients[
                ["ForcaShitese", "Klienti", "Avg_Monthly", "Recent_Sales"]
            ].copy()
            risk_display["Avg_Monthly"] = risk_display["Avg_Monthly"].map(
                "{:,.2f} Lek".format
            )
            risk_display["Recent_Sales"] = risk_display["Recent_Sales"].map(
                "{:,.2f} Lek".format
            )

            st.dataframe(
                risk_display.rename(
                    columns={
                        "ForcaShitese": "Agjenti",
                        "Avg_Monthly": "Mesatarja Mujore",
                        "Recent_Sales": "Shitjet 90 Ditët e Fundit",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.success("✅ Nuk ka klientë në rrezik aktualisht.")

    with tab3:
        st.subheader(f"Klientët Stabilë ({len(stable_clients)})")
        st.success(
            "🟢 Klientë që mbajnë ritëm të rregullt blerjesh dhe janë jashtë zonës së rrezikut."
        )
        if not stable_clients.empty:
            stable_display = stable_clients[
                ["ForcaShitese", "Klienti", "Total_Sales", "Last_Date"]
            ].copy()
            stable_display["Total_Sales"] = stable_display["Total_Sales"].map(
                "{:,.2f} Lek".format
            )
            stable_display["Last_Date"] = stable_display["Last_Date"].dt.strftime(
                "%d/%m/%Y"
            )

            st.dataframe(
                stable_display.rename(
                    columns={
                        "ForcaShitese": "Agjenti",
                        "Total_Sales": "Totali i Shitjeve",
                        "Last_Date": "Blerja e Fundit",
                    }
                ),
                use_container_width=True,
            )
