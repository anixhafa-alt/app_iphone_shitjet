import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta


def render_mundesite_shitjes(df):
    st.title("🎯 Analiza e Mundësive të Shitjes & Klientët Pasivë")
    st.markdown(
        "Identifikimi i klientëve që kanë ndaluar blerjet ose kanë rënie drastike të volumit."
    )

    # --- 1. LOGJIKA E PROCESIMIT TË TË DHËNAVE (E marrë nga kodi yt) ---
    # Sigurohemi që datat janë në rregull
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    current_year = 2026  # Përshtatur me vitin aktual të sistemit tuaj
    today = datetime(current_year, 5, 21)  # Data korrente e aplikacionit tuaj

    # Filtro vetëm vitin e fundit për analizë pasiviteti
    start_date_analysis = today - timedelta(days=365)
    df_filtered = df[df["Data"] >= start_date_analysis].copy()

    if df_filtered.empty:
        st.warning(
            "⚠️ Nuk ka të dhënë në 12 muajt e fundit për të kryer analizën e mundësive."
        )
        return

    # Agregimi sipas Klientit dhe Agjentit
    # Shënim: Sigurohu që kolonat 'Klienti', 'Agjenti', 'Vlera_Neto' (ose si e ke emrin e kolonës së vlerës) ekzistojnë
    vlera_col = (
        "Vlera_Neto"
        if "Vlera_Neto" in df.columns
        else df.select_dtypes(include=[np.number]).columns[0]
    )
    agjent_col = "Agjenti" if "Agjenti" in df.columns else "Zona"

    client_summary = (
        df_filtered.groupby(["Klienti", agjent_col])
        .agg(
            Total_Sales=(vlera_col, "sum"),
            Last_Date=("Data", "max"),
            First_Date=("Data", "min"),
            Faseta_Count=("Data", "count"),
        )
        .reset_index()
    )

    client_summary["Days_Inactive"] = (today - client_summary["Last_Date"]).dt.days

    # Definimi i Statusit (Kriteret e tua)
    def dëgjo_statusin(row):
        if row["Days_Inactive"] > 90:
            return "danger"  # Kuqe: Mbi 3 muaj pa blerë
        elif row["Days_Inactive"] > 45:
            return "warning"  # Portokalli: 1.5 - 3 muaj pa blerë
        return "normal"

    client_summary["Status"] = client_summary.apply(dëgjo_statusin, axis=1)

    # Filtrojmë vetëm ata që kanë probleme (danger dhe warning)
    opportunities = client_summary[
        client_summary["Status"].isin(["danger", "warning"])
    ].copy()
    opportunities["Last_Date"] = opportunities["Last_Date"].dt.strftime("%Y-%m-%d")

    # --- 2. STRUKTURIMI PËR HTML-IN TËND ---
    # Kthejmë të dhënat në strukturën hierarkike Agjent -> Klientë
    hierarchy = {}
    for _, r in opportunities.iterrows():
        agj = r[agjent_col]
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

    # Konvertojmë në JSON për t'ia kaluar Javascript-it tënd
    json_data = json.dumps(hierarchy)

    # --- 3. INJEKTIMI I INTERFEJSIT TËND HTML / CSS / JS ---
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            .agjent-section {{
                background: #ffffff; border-radius: 8px; padding: 15px; 
                margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border-left: 5px solid #1e3a8a;
            }}
            .agjent-header {{
                font-size: 1.2rem; font-weight: bold; color: #1e3a8a;
                cursor: pointer; display: flex; justify-content: space-between; align-items: center;
            }}
            .client-grid {{
                display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 12px; margin-top: 10px;
            }}
            .client-card {{
                padding: 12px; border-radius: 6px; border: 1px solid #e5e7eb; background: #f9fafb;
            }}
            .client-card.danger {{ border-top: 4px solid #ef4444; }}
            .client-card.warning {{ border-top: 4px solid #f59e0b; }}
            .client-name {{ font-weight: bold; color: #374151; font-size: 0.95rem; }}
            .badge {{
                font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: bold; text-transform: uppercase;
            }}
            .bg-danger {{ background: #fee2e2; color: #991b1b; }}
            .bg-warning {{ background: #fef3c7; color: #92400e; }}
            .info-row {{ font-size: 0.85rem; color: #6b7280; margin-top: 4px; }}
            .val-bold {{ font-weight: bold; color: #111827; }}
            .action-row {{ display: flex; gap: 8px; margin-top: 10px; }}
            .btn-act {{
                flex: 1; text-align: center; font-size: 0.8rem; padding: 6px;
                border-radius: 4px; text-decoration: none; font-weight: 500;
            }}
            .btn-call {{ background: #ecfdf5; color: #065f46; }}
            .btn-plan {{ background: #eff6ff; color: #1e40af; }}
        </style>
    </head>
    <body>

    <div id="opportunities-container"></div>

    <script>
        const data = {json_data};
        const container = document.getElementById('opportunities-container');
        
        let html = '';
        Object.keys(data).forEach(agjent => {{
            const kliente = data[agjent];
            html += `
            <div class="agjent-section">
                <div class="agjent-header">
                    <span><i class="fa-solid fa-user-tie"></i> ${{agjent}} (${{kliente.length}} mundësi)</span>
                </div>
                <div class="client-grid">`;
                
            kliente.forEach(d => {{
                const badgeClass = d.Status === 'danger' ? 'bg-danger' : 'bg-warning';
                const badgeText = d.Status === 'danger' ? 'Kritik (Pasiv)' : 'Nën Monitorim';
                
                html += `
                <div class="client-card ${{d.Status}}">
                    <div style="display:flex; justify-content:space-between; align-items:start;">
                        <div class="client-name">${{d.Klienti}}</div>
                        <span class="badge ${{badgeClass}}">${{badgeText}}</span>
                    </div>
                    <div class="info-row">
                        <i class="fa-solid fa-calendar-xmark"></i> <span class="val-bold">${{d.Days_Inactive}}</span> ditë pa blerë
                    </div>
                    <div class="info-row">
                        <span>Tot. Hist: <span class="val-bold">${{d.Total_Sales}} Lek</span></span>
                    </div>
                    <div class="info-row">
                        <span>Blerja e fundit: ${{d.Last_Date}}</span>
                    </div>
                    <div class="action-row">
                        <a href="tel:+" class="btn-act btn-call"><i class="fa-solid fa-phone"></i> Telefono</a>
                    </div>
                </div>`;
            }});
            
            html += `</div></div>`;
        }});
        
        container.innerHTML = html || '<p>Nuk ka klientë pasivë në këtë periudhë.</p>';
    </script>
    </body>
    </html>
    """

    # Renderimi i sigurt i HTML brenda Streamlit
    import streamlit.components.v1 as components

    components.html(html_template, height=800, scroller=True)
