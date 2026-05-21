mport pandas as pd
import numpy as np
import time
import json
import sys
import os
from datetime import datetime, timedelta

# --- KONFIGURIME ---
FILE_NAME_XLSB = 'SAD-DATAbase1.xlsb'

start_time = time.time()
print("--- FILLOI ANALIZA E MUNDËSIVE V3 (DEFAULT COLLAPSED) ---")

# 1. LEXIMI
print(f"Duke lexuar {FILE_NAME_XLSB}...")
try:
    df = pd.read_excel(FILE_NAME_XLSB, engine='pyxlsb', sheet_name='Sheet1')
    print(f"✅ U lexua XLSB: {len(df)} rreshta.")
except:
    print(f"❌ Gabim: Nuk u gjet fajli '{FILE_NAME_XLSB}'.")
    sys.exit()

# 2. PASTRIMI
df.columns = df.columns.str.strip().str.replace('"', '')

if pd.api.types.is_numeric_dtype(df['Data']):
    df['Data'] = pd.to_datetime(df['Data'], unit='D', origin='1899-12-30').dt.normalize()
else:
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce').dt.normalize()

current_year = datetime.now().year
start_date_analysis = datetime(current_year - 3, 1, 1)
df = df[df['Data'] >= start_date_analysis]

for col in ['TotalRresht', 'kg']:
    if col in df.columns:
        if df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        df[col] = 0.0

df = df[df['TotalRresht'] > 0]

# 3. ANALIZA
print("Duke analizuar sjelljen e klientëve...")
max_date = df['Data'].max()

client_stats = df.groupby(['ForcaShitese', 'Klienti']).agg(
    Last_Date=('Data', 'max'),
    First_Date=('Data', 'min'),
    Total_Sales=('TotalRresht', 'sum'),
    Sales_Count=('TotalRresht', 'count')
).reset_index()

client_stats['Days_Inactive'] = (max_date - client_stats['Last_Date']).dt.days
client_stats['Months_Active'] = ((client_stats['Last_Date'] - client_stats['First_Date']).dt.days / 30).astype(int)
client_stats['Months_Active'] = client_stats['Months_Active'].replace(0, 1)
client_stats['Avg_Monthly'] = client_stats['Total_Sales'] / client_stats['Months_Active']

# --- SEGMENTET ---
# 1. Të Fjetur
churn_clients = client_stats[
    (client_stats['Days_Inactive'] > 60) & 
    (client_stats['Total_Sales'] > 50000)
].copy()
churn_clients['Status'] = 'Fjetur'

# 2. Në Rrezik
last_90_days = max_date - timedelta(days=90)
recent_sales = df[df['Data'] >= last_90_days].groupby(['ForcaShitese', 'Klienti'])['TotalRresht'].sum().reset_index()
recent_sales.rename(columns={'TotalRresht': 'Recent_Sales'}, inplace=True)

risk_analysis = pd.merge(client_stats, recent_sales, on=['ForcaShitese', 'Klienti'], how='left').fillna(0)

risk_clients = risk_analysis[
    (risk_analysis['Days_Inactive'] <= 45) & 
    (risk_analysis['Recent_Sales'] < (risk_analysis['Avg_Monthly'] * 3 * 0.6)) & 
    (risk_analysis['Avg_Monthly'] > 5000)
].copy()
risk_clients['Status'] = 'Rrezik'

final_opps = pd.concat([
    churn_clients[['ForcaShitese', 'Klienti', 'Last_Date', 'Total_Sales', 'Days_Inactive', 'Status']],
    risk_clients[['ForcaShitese', 'Klienti', 'Last_Date', 'Total_Sales', 'Days_Inactive', 'Status']]
])

final_opps['Last_Date'] = final_opps['Last_Date'].dt.strftime('%d/%m/%Y')
final_opps = final_opps.sort_values(by='Total_Sales', ascending=False)

json_str = final_opps.to_json(orient='records')
agjentet_unike = sorted(final_opps['ForcaShitese'].unique())

# 4. HTML
print("Duke ndërtuar ndërfaqen e grupuar (Collapsed)...")

html_content = f"""
<!DOCTYPE html>
<html lang="sq">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Mundësitë</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #f8fafc; --card: #ffffff; --text: #1e293b; --danger: #ef4444; --warning: #f59e0b; --success: #10b981; --primary: #3b82f6; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 12px; -webkit-tap-highlight-color: transparent; }}
        
        .header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
        .title {{ font-size: 1.4rem; font-weight: 800; color: #1e293b; margin: 0; }}
        .btn-home {{ background: white; border: 1px solid #e2e8f0; padding: 8px 12px; border-radius: 10px; color: #334155; display: flex; align-items: center; transition: 0.2s; text-decoration:none; }}
        
        .filters {{ display: flex; gap: 10px; margin-bottom: 20px; overflow-x: auto; padding-bottom: 5px; }}
        .filter-btn {{ padding: 8px 16px; border-radius: 20px; border: none; font-weight: 600; font-size: 0.9rem; cursor: pointer; white-space: nowrap; transition: 0.2s; }}
        .btn-all {{ background: var(--primary); color: white; }}
        .btn-churn {{ background: white; color: var(--danger); border: 1px solid var(--danger); }}
        .btn-risk {{ background: white; color: var(--warning); border: 1px solid var(--warning); }}
        
        .filter-btn.active {{ transform: scale(1.05); box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .btn-churn.active {{ background: var(--danger); color: white; }}
        .btn-risk.active {{ background: var(--warning); color: white; }}

        .search-box {{ width: 100%; padding: 12px; border-radius: 12px; border: 1px solid #cbd5e1; margin-bottom: 15px; font-size: 1rem; box-sizing: border-box; }}

        /* AGENT GROUP STYLES */
        .agent-group {{ margin-bottom: 15px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }}
        .agent-header {{ 
            padding: 15px; 
            background: #f1f5f9; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            cursor: pointer; 
            font-weight: 700; 
            color: #334155;
            border-bottom: 1px solid #e2e8f0;
        }}
        .agent-header:active {{ background: #e2e8f0; }}
        .agent-count {{ background: var(--primary); color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; margin-left: 5px; }}
        
        /* DEFAULT HIDDEN */
        .agent-body {{ display: none; padding: 10px; background: #fff; }}

        /* CLIENT CARD STYLES */
        .client-card {{ 
            border: 1px solid #e2e8f0; 
            border-radius: 8px; 
            padding: 12px; 
            margin-bottom: 10px; 
            border-left: 4px solid #ccc; 
            background: #fff;
        }}
        .client-card.Fjetur {{ border-left-color: var(--danger); background: #fff5f5; }}
        .client-card.Rrezik {{ border-left-color: var(--warning); background: #fffbeb; }}
        
        .card-top {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
        .client-name {{ font-weight: 700; font-size: 0.95rem; color: #0f172a; }}
        .badge {{ padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 800; text-transform: uppercase; }}
        .bg-Fjetur {{ background: #fee2e2; color: #991b1b; }}
        .bg-Rrezik {{ background: #fef3c7; color: #92400e; }}
        
        .info-row {{ font-size: 0.8rem; color: #64748b; display: flex; justify-content: space-between; margin-top: 4px; }}
        .val-bold {{ font-weight: 700; color: #334155; }}
        
        .action-row {{ margin-top: 10px; display: flex; gap: 8px; }}
        .btn-act {{ flex: 1; padding: 6px; text-align: center; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-decoration: none; border: 1px solid transparent; }}
        .btn-call {{ background: white; border-color: #cbd5e1; color: #334155; }}
        .btn-plan {{ background: var(--primary); color: white; }}

        .icon-state {{ transition: transform 0.2s; font-size: 0.9rem; color: #94a3b8; }}
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h1 class="title">Mundësitë</h1>
            <span style="font-size:0.8rem; color:#64748b">Analiza sipas Agjentëve</span>
        </div>
        <a href="INDEX.html" class="btn-home"><i class="fa-solid fa-house"></i></a>
    </div>

    <div class="filters">
        <button class="filter-btn btn-all active" onclick="filterType('all', this)">Të Gjitha</button>
        <button class="filter-btn btn-churn" onclick="filterType('Fjetur', this)">Ri-aktivizim</button>
        <button class="filter-btn btn-risk" onclick="filterType('Rrezik', this)">Në Rrezik</button>
    </div>

    <input type="text" id="search" class="search-box" placeholder="Kërko klient ose agjent..." onkeyup="renderList()">

    <div id="listArea"></div>

<script>
const data = {json_str};
let currentFilter = 'all';

function formatNum(n) {{
    if(n >= 1000000) return (n/1000000).toFixed(1) + 'M'; 
    if(n >= 1000) return (n/1000).toFixed(1) + 'k'; 
    return n.toFixed(0);
}}

function filterType(type, btn) {{
    currentFilter = type;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderList();
}}

function toggleAgent(id, el) {{
    const body = document.getElementById(id);
    const isOpen = body.style.display === 'block';
    body.style.display = isOpen ? 'none' : 'block';
    const icon = el.querySelector('.icon-state');
    if(icon) icon.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
}}

function renderList() {{
    const search = document.getElementById('search').value.toLowerCase();
    const container = document.getElementById('listArea');
    container.innerHTML = '';

    const filtered = data.filter(d => {{
        const matchType = currentFilter === 'all' || d.Status === currentFilter;
        const matchSearch = d.Klienti.toLowerCase().includes(search) || d.ForcaShitese.toLowerCase().includes(search);
        return matchType && matchSearch;
    }});

    if(filtered.length === 0) {{
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#94a3b8">Nuk u gjetën mundësi.</div>';
        return;
    }}

    let grouped = {{}};
    filtered.forEach(d => {{
        if(!grouped[d.ForcaShitese]) grouped[d.ForcaShitese] = [];
        grouped[d.ForcaShitese].push(d);
    }});

    const sortedAgents = Object.keys(grouped).sort((a,b) => grouped[b].length - grouped[a].length);

    let html = '';
    sortedAgents.forEach((agent, idx) => {{
        const clients = grouped[agent];
        const agentId = `ag_${{idx}}`;
        
        html += `
        <div class="agent-group">
            <div class="agent-header" onclick="toggleAgent('${{agentId}}', this)">
                <div>
                    <i class="fa-solid fa-user-tie" style="margin-right:8px; color:#64748b"></i> ${{agent}}
                    <span class="agent-count">${{clients.length}}</span>
                </div>
                <i class="fa-solid fa-chevron-down icon-state"></i>
            </div>
            
            <div id="${{agentId}}" class="agent-body">`;
            
            clients.forEach(d => {{
                const isChurn = d.Status === 'Fjetur';
                const badgeText = isChurn ? 'RI-AKTIVIZO' : 'PO BIE';
                const descText = isChurn 
                    ? `<span style="color:#ef4444"><i class="fa-regular fa-clock"></i> ${{-d.Days_Inactive}} ditë pa blerje</span>` 
                    : `<span style="color:#f59e0b"><i class="fa-solid fa-arrow-trend-down"></i> Rënie drastike</span>`;

                html += `
                <div class="client-card ${{d.Status}}">
                    <div class="card-top">
                        <div class="client-name">${{d.Klienti}}</div>
                        <div class="badge bg-${{d.Status}}">${{badgeText}}</div>
                    </div>
                    
                    <div class="info-row">
                        ${{descText}}
                        <span>Tot. Hist: <span class="val-bold">${{formatNum(d.Total_Sales)}}</span></span>
                    </div>
                    <div class="info-row">
                        <span>Fundit: ${{d.Last_Date}}</span>
                    </div>

                    <div class="action-row">
                        <a href="tel:+" class="btn-act btn-call"><i class="fa-solid fa-phone"></i> Telefono</a>
                        <a href="PLANIFIKIMI_DETAJUAR_V8.html" class="btn-act btn-plan"><i class="fa-solid fa-bullseye"></i> Planifiko</a>
                    </div>
                </div>`;
            }});

        html += `</div></div>`;
    }});

    container.innerHTML = html;
}}

renderList();

</script>
</body>
</html>
"""

#with open('MUNDESITE.html', "w", encoding="utf-8") as f:
    #f.write(html_content)

#print(f"--- SUCCESS! U krijua: 'MUNDESITE.html' ---")