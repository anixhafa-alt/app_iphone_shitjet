import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components


def render_mundesite_shitjes(df):
    st.title("🎯 Analiza e Mundësive të Shitjes & Klientët Pasivë")
    st.markdown(
        "Identifikimi i klientëve që kanë ndaluar blerjet ose kanë rënie drastike të volumit."
    )

    # --- KONTROLLI I DATAFRAME ---
    if df is None or df.empty:
        st.error(
            "❌ Nuk ka të dhëna të disponueshme për analizë (DataFrame është bosh)."
        )
        return

    # --- AUTO-DETECT DHE KORRIGJIMI I KOLONAVE ---
    # Kjo parandalon crash-in nëse kolonat janë me të mëdha/vogla
    df.columns = df.columns.str.strip()

    col_mapping = {
        "Data": next(
            (c for c in df.columns if c.lower() in ["data", "date", "faturimi"]), None
        ),
        "Klienti": next(
            (
                c
                for c in df.columns
                if c.lower() in ["klienti", "klient", "customer", "emri_klientit"]
            ),
            None,
        ),
        "Agjenti": next(
            (
                c
                for c in df.columns
                if c.lower() in ["agjenti", "agjent", "zona", "sales_rep"]
            ),
            None,
        ),
        "Vlera": next(
            (
                c
                for c in df.columns
                if c.lower() in ["vlera_neto", "vlera", "total", "neto", "sasia_kg"]
            ),
            None,
        ),
    }

    # Kontroll nëse mungon ndonjë kolonë kritike
    missing_cols = [k for k, v in col_mapping.items() if v is None]
    if missing_cols:
        st.error(f"❌ Nuk u gjetën dot kolonat automatikisht. Mungojnë: {missing_cols}")
        st.info(f"Kolonat aktuale në databazë janë: `{list(df.columns)}`")
        return

    # Krijojmë një kopje të pastër me emrat e duhur për punë
    df_working = pd.DataFrame(
        {
            "Data": df[col_mapping["Data"]],
            "Klienti": df[col_mapping["Klienti"]],
            "Agjenti": df[col_mapping["Agjenti"]],
            "Vlera": df[col_mapping["Vlera"]],
        }
    ).copy()

    # --- PASTRIMI I DATAVE ---
    if not pd.api.types.is_datetime64_any_dtype(df_working["Data"]):
        if pd.api.types.is_numeric_dtype(df_working["Data"]):
            df_working["Data"] = pd.to_datetime(
                df_working["Data"], unit="D", origin="1899-12-30"
            ).dt.normalize()
        else:
            df_working["Data"] = pd.to_datetime(
                df_working["Data"], dayfirst=True, errors="coerce"
            ).dt.normalize()

    # Heqim rreshtat ku data ose klienti është null
    df_working = df_working.dropna(subset=["Data", "Klienti"])

    # --- LOGJIKA E ANALIZËS (Viti aktual i sistemit 2026) ---
    today = datetime(2026, 5, 21)
    start_date_analysis = today - timedelta(days=365)
    df_filtered = df_working[df_working["Data"] >= start_date_analysis].copy()

    if df_filtered.empty:
        st.warning(
            "⚠️ Nuk u gjet asnjë shitje në 12 muajt e fundit (bazuar në datën e sistemit 2026-05-21)."
        )
        return

    # Agregimi
    client_summary = (
        df_filtered.groupby(["Klienti", "Agjenti"])
        .agg(Total_Sales=("Vlera", "sum"), Last_Date=("Data", "max"))
        .reset_index()
    )

    client_summary["Days_Inactive"] = (today - client_summary["Last_Date"]).dt.days

    # Kriteret e Statusit
    def target_status(days):
        if days > 90:
            return "danger"
        if days > 45:
            return "warning"
        return "normal"

    client_summary["Status"] = client_summary["Days_Inactive"].apply(target_status)

    # Filtrojmë vetëm klientët pasivë (danger dhe warning)
    opportunities = client_summary[
        client_summary["Status"].isin(["danger", "warning"])
    ].copy()

    if opportunities.empty:
        st.success("✅ Shkëlqyeshëm! Nuk u gjet asnjë klient pasiv në këtë periudhë.")
        return

    # Formatimi i datave për JSON
    opportunities["Last_Date"] = opportunities["Last_Date"].dt.strftime("%Y-%m-%d")

    # Sigurohemi që nuk ka vlera NaN që thyejnë JS-in
    opportunities["Total_Sales"] = opportunities["Total_Sales"].fillna(0).astype(float)
    opportunities["Days_Inactive"] = (
        opportunities["Days_Inactive"].fillna(0).astype(int)
    )
    opportunities["Klienti"] = (
        opportunities["Klienti"].astype(str).str.replace("'", "\\'")
    )  # Shpëton thonjëzat
    opportunities["Agjenti"] = (
        opportunities["Agjenti"].astype(str).str.replace("'", "\\'")
    )

    # --- NDËRTIMI I HIERARKISË JSON ---
    hierarchy = {}
    for _, r in opportunities.iterrows():
        agj = r["Agjenti"]
        if agj not in hierarchy:
            hierarchy[agj] = []
        hierarchy[agj].append(
            {
                "Klienti": r["Klienti"],
                "Total_Sales": round(r["Total_Sales"], 2),
                "Last_Date": r["Last_Date"],
                "Days_Inactive": int(r["Days_Inactive"]),
                "Status": r["Status"],
            }
        )

    json_data = json.dumps(hierarchy)

    # --- HTML / CSS / JS ---
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; background: #f3f4f6; margin: 10px; padding: 0; }}
            .agjent-section {{
                background: #ffffff; border-radius: 8px; padding: 15px; 
                margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border-left: 5px solid #1e3a8a;
            }}
            .agjent-header {{
                font-size: 1.15rem; font-weight: bold; color: #1e3a8a;
                padding-bottom: 10px; border-bottom: 1px solid #e5e7eb;
                display: flex; justify-content: space-between; align-items: center;
            }}
            .client-grid {{
                display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 12px; margin-top: 12px;
            }}
            .client-card {{
                padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb; background: #f9fafb;
                display: flex; flex-direction: column; justify-content: space-between;
            }}
            .client-card.danger {{ border-top: 4px solid #ef4444; }}
            .client-card.warning {{ border-top: 4px solid #f59e0b; }}
            .card-top {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px; }}
            .client-name {{ font-weight: bold; color: #374151; font-size: 0.95rem; max-width: 70%; }}
            .badge {{
                font-size: 0.7rem; padding: 3px 6px; border-radius: 4px; font-weight: bold; text-transform: uppercase; white-space: nowrap;
            }}
            .bg-danger {{ background: #fee2e2; color: #991b1b; }}
            .bg-warning {{ background: #fef3c7; color: #92400e; }}
            .info-row {{ font-size: 0.85rem; color: #6b7280; margin-top: 4px; }}
            .val-bold {{ font-weight: bold; color: #111827; }}
            .action-row {{ display: flex; gap: 8px; margin-top: 12px; }}
            .btn-act {{
                flex: 1; text-align: center; font-size: 0.8rem; padding: 6px;
                border-radius: 4px; text-decoration: none; font-weight: 500; display: inline-block;
            }}
            .btn-call {{ background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }}
        </style>
    </head>
    <body>

    <div id="opportunities-container"></div>

    <script>
        try {{
            const data = {json_data};
            const container = document.getElementById('opportunities-container');
            
            let html = '';
            const keys = Object.keys(data);
            
            if(keys.length === 0) {{
                container.innerHTML = '<p style="padding:20px; color:#6b7280;">Nuk u gjetën të dhëna për treguesit e përzgjedhur.</p>';
            }} else {{
                keys.forEach(agjent => {{
                    const kliente = data[agjent];
                    html += `
                    <div class="agjent-section">
                        <div class="agjent-header">
                            <span><i class="fa-solid fa-user-tie"></i> ${{agjent}}</span>
                            <span style="font-size:0.9rem; background:#eff6ff; color:#1e40af; padding:2px 8px; border-radius:12px;">${{kliente.length}} mundësi</span>
                        </div>
                        <div class="client-grid">`;
                        
                    kliente.forEach(d => {{
                        const badgeClass = d.Status === 'danger' ? 'bg-danger' : 'bg-warning';
                        const badgeText = d.Status === 'danger' ? 'Kritik (Pasiv)' : 'Nën Monitorim';
                        
                        html += `
                        <div class="client-card ${{d.Status}}">
                            <div class="card-top">
                                <div class="client-name">${{d.Klienti}}</div>
                                <span class="badge ${{badgeClass}}">${{badgeText}}</span>
                            </div>
                            <div class="info-row">
                                <i class="fa-solid fa-calendar-xmark" style="color:#9ca3af;"></i> Pa blerë: <span class="val-bold">${{d.Days_Inactive}}</span> ditë
                            </div>
                            <div class="info-row">
                                <i class="fa-solid fa-money-bill-wave" style="color:#9ca3af;"></i> Tot. Hist: <span class="val-bold">${{d.Total_Sales}} Lek</span>
                            </div>
                            <div class="info-row">
                                <i class="fa-solid fa-clock" style="color:#9ca3af;"></i> Fundit: ${{d.Last_Date}}
                            </div>
                            <div class="action-row">
                                <a href="tel:+" class="btn-act btn-call"><i class="fa-solid fa-phone"></i> Telefono</a>
                            </div>
                        </div>`;
                    }});
                    
                    html += `</div></div>`;
                }});
                container.innerHTML = html;
            }}
        }} catch(err) {{
            document.getElementById('opportunities-container').innerHTML = 
                '<div style="color:red; padding:20px; background:#ffeeef; border-radius:5px;"><b>Gabim në renderimin JS:</b> ' + err.message + '</div>';
        }}
    </script>
    </body>
    </html>
    """

    # Renderimi në Streamlit
    components.html(html_template, height=1000, scroller=True)
