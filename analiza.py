import streamlit as st
import pandas as pd
import numpy as np
import json
import streamlit.components.v1 as components


def render_analiza_klienteve(df_raw):
    st.title("📊 Dashboard Ekzekutiv i Shitjeve")
    st.markdown(
        "Analizë e detajuar e shitjeve, volumit në KG dhe kategorive të produkteve."
    )

    if df_raw is None or df_raw.empty:
        st.error("❌ Nuk u gjetën të dhënat nga skedari SAD-DATAbase1.xlsb.")
        return

    # --- 1. PROCESIMI I TË DHËNAVE (Ekzaktësisht si kodi yt) ---
    df = df_raw.copy()
    df.columns = df.columns.str.strip().str.replace('"', "")

    if pd.api.types.is_numeric_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], unit="D", origin="1899-12-30")
    else:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    df = df.dropna(subset=["Data"])

    # Konvertimet numerike
    cols_numerike = ["TotalRresht", "Sasia", "kg"]
    for c in cols_numerike:
        if c in df.columns:
            if df[c].dtype == "object":
                df[c] = df[c].astype(str).str.replace(",", "", regex=False)
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0.0

    # Krijimi i kolonave të kohës si te kodi yt
    df["Viti"] = df["Data"].dt.year
    df["Muaji_Nr"] = df["Data"].dt.month

    muajt_shqip = {
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
    df["Muaji"] = df["Muaji_Nr"].map(muajt_shqip)

    # Sigurohemi që ka kolonë Kategoria_Finale ose KATEG.
    if "Kategoria_Finale" not in df.columns and "KATEG." in df.columns:
        df["Kategoria_Finale"] = df["KATEG."]
    elif "Kategoria_Finale" not in df.columns:
        df["Kategoria_Finale"] = "ETJ"

    # Përgatitja e të dhënave për JSON (Heqim thonjëzat që thyejnë JS)
    df["Klienti"] = (
        df["Klienti"].astype(str).str.replace("'", "\\'").str.replace('"', '\\"')
    )
    df["ForcaShitese"] = (
        df["ForcaShitese"].astype(str).str.replace("'", "\\'").str.replace('"', '\\"')
    )
    df["Kategoria_Finale"] = (
        df["Kategoria_Finale"]
        .astype(str)
        .str.replace("'", "\\'")
        .str.replace('"', '\\"')
    )

    # Eksporti në formatin JSON që pret kodi yt në HTML
    json_cols = [
        "Data",
        "Viti",
        "Muaji",
        "Muaji_Nr",
        "ForcaShitese",
        "Klienti",
        "Kategoria_Finale",
        "TotalRresht",
        "kg",
    ]
    records = df[json_cols].copy()
    records["Data"] = records["Data"].dt.strftime("%Y-%m-%d")

    json_data_str = records.to_json(orient="records")

    # --- 2. INTERFEJSI HTML / JS / CHART.JS (100% i joti, pa asnjë ndryshim) ---
    html_template = f"""
    <!DOCTYPE html>
    <html lang="sq">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ --primary: #1e3a8a; --bg: #f8fafc; --card: #ffffff; --text: #0f172a; }}
            body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); margin:0; padding:10px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 15px; }}
            .card {{ background: var(--card); padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); border: 1px solid #e2e8f0; }}
            .card-title {{ font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; }}
            .card-value {{ font-size: 1.6rem; font-weight: 700; color: var(--primary); margin-top: 5px; }}
            .chart-container {{ position: relative; height: 320px; width: 100%; background: white; padding: 10px; border-radius: 10px; border: 1px solid #e2e8f0; box-sizing: border-box; }}
            .flex-charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 15px; margin-bottom: 20px; }}
            select, input {{ padding: 8px; border-radius: 6px; border: 1px solid #cbd5e1; width: 100%; box-sizing: border-box; font-size: 0.9rem; }}
            .filter-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 15px; background: white; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; font-size: 0.9rem; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f1f5f9; font-weight: 600; color: #334155; }}
            .home-btn {{ background: #e2e8f0; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-bottom: 10px; display: inline-flex; align-items: center; gap: 5px; }}
        </style>
    </head>
    <body>

        <button class="home-btn" onclick="resetFilters()"><i class="fa-solid fa-house"></i> Reset Filters</button>

        <div class="filter-grid">
            <div><label style="font-size:0.75rem; font-weight:600; color:#64748b;">VITI</label><select id="fViti" onchange="updateDashboard()"><option value="all">Gjithë Vitet</option></select></div>
            <div><label style="font-size:0.75rem; font-weight:600; color:#64748b;">MUAJI</label><select id="fMuaji" onchange="updateDashboard()"><option value="all">Gjithë Muajt</option></select></div>
            <div><label style="font-size:0.75rem; font-weight:600; color:#64748b;">AGJENTI</label><select id="fAgjent" onchange="updateDashboard()"><option value="all">Gjithë Agjentët</option></select></div>
            <div><label style="font-size:0.75rem; font-weight:600; color:#64748b;">METRIKA</label><select id="fMetrika" onchange="updateDashboard()"><option value="lek">Lek (Vlerë)</option><option value="kg">KG (Volum)</option></select></div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Xhiro / Volumi Total</div><div class="card-value" id="kpiTotal">0</div></div>
            <div class="card"><div class="card-title">Numri i Faturave</div><div class="card-value" id="kpiFatura">0</div></div>
            <div class="card"><div class="card-title">Klientë Aktivë</div><div class="card-value" id="kpiKliente">0</div></div>
        </div>

        <div class="flex-charts">
            <div class="chart-container"><canvas id="lineChart"></canvas></div>
            <div class="chart-container"><canvas id="pieChart"></canvas></div>
        </div>

        <div class="card" style="padding:0; overflow-x:auto;">
            <table id="topTable">
                <thead><tr><th>Renditja</th><th id="tableDynamicHeader">Klienti / Agjenti</th><th>Ecuria Lokale</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

    <script>
        const rawData = {json_data_str};
        let lineChart, pieChart;

        // Mbush filtrat dinamikisht
        const vitet = [...new Set(rawData.map(d => d.Viti))].sort((a,b)=>b-a);
        const agjentet = [...new Set(rawData.map(d => d.ForcaShitese))].sort();
        const muajt = ["Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor"];

        const selViti = document.getElementById('fViti');
        vitet.forEach(v => selViti.add(new Option(v, v)));

        const selMuaji = document.getElementById('fMuaji');
        muajt.forEach(m => selMuaji.add(new Option(m, m)));

        const selAgjent = document.getElementById('fAgjent');
        agjentet.forEach(a => selAgjent.add(new Option(a, a)));

        function formatNum(n) {{
            if(n >= 1000000) return (n/1000000).toFixed(2) + ' M';
            if(n >= 1000) return (n/1000).toFixed(1) + ' k';
            return n.toLocaleString('de-DE', {{maximumFractionDigits:0}});
        }}

        function resetFilters() {{
            document.getElementById('fViti').value = 'all';
            document.getElementById('fMuaji').value = 'all';
            document.getElementById('fAgjent').value = 'all';
            document.getElementById('fMetrika').value = 'lek';
            updateDashboard();
        }}

        function updateDashboard() {{
            const viti = document.getElementById('fViti').value;
            const muaji = document.getElementById('fMuaji').value;
            const agjent = document.getElementById('fAgjent').value;
            const metric = document.getElementById('fMetrika').value;

            let filtered = rawData.filter(d => {{
                return (viti === 'all' || d.Viti == viti) &&
                       (muaji === 'all' || d.Muaji === muaji) &&
                       (agjent === 'all' || d.ForcaShitese === agjent);
            }});

            // Llogarit KPI-të
            let totalVal = filtered.reduce((acc, d) => acc + (metric === 'lek' ? d.TotalRresht : d.kg), 0);
            let fatCount = filtered.length;
            let klienteUnik = [...new Set(filtered.map(d => d.Klienti))].length;

            document.getElementById('kpiTotal').innerText = formatNum(totalVal) + (metric==='lek' ? ' Lek' : ' KG');
            document.getElementById('kpiFatura').innerText = fatCount.toLocaleString();
            document.getElementById('kpiKliente').innerText = klienteUnik.toLocaleString();

            // RENDERIMI I GRAFIKËVE (Sipas logjikës sate Chart.js)
            renderCharts(filtered, metric, agjent);
        }}

        function renderCharts(filtered, metric, agjent) {{
            const colors = ['#1e3a8a', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];
            
            // 1. Line Chart - Ecuria sipas muajve
            let labels = ["Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor"];
            let yearsInDoc = [...new Set(filtered.map(d => d.Viti))].sort();
            
            let lineDatasets = [];
            yearsInDoc.forEach((yr, i) => {{
                let vals = new Array(12).fill(0);
                labels.forEach((m, mIdx) => {{
                    vals[mIdx] = filtered.filter(d => d.Viti == yr && d.Muaji === m)
                                         .reduce((acc, d) => acc + (metric==='lek' ? d.TotalRresht : d.kg), 0);
                }});
                lineDatasets.push({{
                    label: yr,
                    data: vals,
                    borderColor: colors[i % colors.length],
                    backgroundColor: 'transparent',
                    borderWidth: 2.5,
                    tension: 0.2
                }});
            }});

            if(lineChart) lineChart.destroy();
            lineChart = new Chart(document.getElementById('lineChart'), {{
                type: 'line',
                data: {{ labels: labels, datasets: lineDatasets }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ title: {{ display: true, text: 'Ecuria Sipas Muajve dhe Viteve' }} }} }}
            }});

            // 2. Pie Chart - Kategoritë
            let catData = {{}};
            filtered.forEach(d => {{
                let val = (metric === 'lek' ? d.TotalRresht : d.kg);
                catData[d.Kategoria_Finale] = (catData[d.Kategoria_Finale] || 0) + val;
            }});
            let catLabels = Object.keys(catData);
            let catVals = Object.values(catData);

            if(pieChart) pieChart.destroy();
            pieChart = new Chart(document.getElementById('pieChart'), {{
                type: 'doughnut',
                data: {{ labels: catLabels, datasets: [{{ data: catVals, backgroundColor: colors }}] }},
                options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right' }} }} }}
            }});

            // 3. Tabela Top Klientë ose Top Agjentë
            const showKlientet = agjent !== 'all' || filtered.length < 500;
            document.getElementById('tableDynamicHeader').innerText = showKlientet ? "Top Klientët" : "Top Agjentët";
            
            let tableData = {{}};
            filtered.forEach(d => {{
                let key = showKlientet ? d.Klienti : d.ForcaShitese;
                let val = (metric === 'lek' ? d.TotalRresht : d.kg);
                tableData[key] = (tableData[key] || 0) + val;
            }});

            let sortedTable = Object.keys(tableData).map(k => ({{ name: k, value: tableData[k] }}))
                                                   .sort((a,b) => b.value - a.value).slice(0, 10);

            let tbody = document.getElementById('topTable').getElementsByTagName('tbody')[0];
            tbody.innerHTML = '';
            sortedTable.forEach((row, idx) => {{
                let r = tbody.insertRow();
                r.insertCell(0).innerText = "#" + (idx + 1);
                r.insertCell(1).innerText = row.name;
                r.insertCell(2).innerText = formatNum(row.value) + (metric==='lek' ? ' Lek' : ' KG');
            }});
        }}

        // Nisja e parë
        updateDashboard();
    </script>
    </body>
    </html>
    """

    # Renderimi në mënyrë të sigurt brenda Streamlit pa bërë faqe të bardhë
    components.html(html_template, height=950, scroller=True)
