import pandas as pd
import numpy as np
import time
import json
import sys
import re

# --- KONFIGURIME ---
FILE_NAME_XLSB = "SAD-DATAbase1.xlsb"

print("--- FILLOI GJENERIMI: PLANIFIKIMI LITE (OPTIMIZUAR PER CELULAR) ---")

# 1. LEXIMI
try:
    # Lexojmë vetëm kolonat e nevojshme për të kursyer memorie
    cols = [
        "Data",
        "ForcaShitese",
        "Klienti",
        "GrupiArtikullit",
        "Artikulli",
        "TotalRresht",
        "kg",
        "Sasia",
        "Anulluar",
    ]
    # Kontrollojme nese ekziston kolona 'Kategoria' ne vend te 'GrupiArtikullit'
    # Për siguri lexojmë gjithçka dhe filtrojmë pas
    df = pd.read_excel(FILE_NAME_XLSB, engine="pyxlsb", sheet_name="Sheet1")
except:
    print(f"❌ Gabim: Nuk u gjet fajli '{FILE_NAME_XLSB}'.")
    sys.exit()

# 2. PASTRIMI DHE OPTIMIZIMI
df.columns = df.columns.str.strip().str.replace('"', "")
if "PershkrimiArtikullit" not in df.columns and "Artikulli" in df.columns:
    df.rename(columns={"Artikulli": "PershkrimiArtikullit"}, inplace=True)

if "Anulluar" in df.columns:
    df["Anulluar_Clean"] = df["Anulluar"].astype(str).str.strip().str.lower()
    df = df[~df["Anulluar_Clean"].isin(["true", "yes", "po", "1", "t", "y"])]

# Heqim kolonat e panevojshme menjëherë
cols_to_keep = [
    "Data",
    "ForcaShitese",
    "Klienti",
    "GrupiArtikullit",
    "Kategoria",
    "PershkrimiArtikullit",
    "TotalRresht",
    "kg",
    "Sasia",
]
existing_cols = [c for c in cols_to_keep if c in df.columns]
df = df[existing_cols]

# Konvertimi i numrave dhe RUMBULLAKOSJA (Kursen hapësirë)
for col in ["TotalRresht", "kg", "Sasia"]:
    if col in df.columns:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce").fillna(0).round(0).astype(int)
        )  # Beje Integer
    else:
        df[col] = 0

# Filtrojmë "Zhurmën" (Rreshta me vlerë 0 ose shumë të vogël)
df = df[df["TotalRresht"] > 10]

# Datat
if pd.api.types.is_numeric_dtype(df["Data"]):
    df["Data"] = pd.to_datetime(df["Data"], unit="D", origin="1899-12-30")
else:
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

df = df.dropna(subset=["Data"])
df = df[df["Data"].dt.year >= 2000]
df["Muaji_Viti"] = df["Data"].dt.strftime("%Y-%m")

# Kategoria
df["Kategoria_Finale"] = "Tjera"
if "Kategoria" in df.columns:
    df["Kategoria"] = df["Kategoria"].astype(str).replace("nan", "")
    if "GrupiArtikullit" in df.columns:
        df["GrupiArtikullit"] = df["GrupiArtikullit"].astype(str).replace("nan", "")
        df["Kategoria_Finale"] = np.where(
            df["Kategoria"] == "", df["GrupiArtikullit"], df["Kategoria"]
        )
    else:
        df["Kategoria_Finale"] = df["Kategoria"]
elif "GrupiArtikullit" in df.columns:
    df["Kategoria_Finale"] = df["GrupiArtikullit"].fillna("Tjera").astype(str)
df["Kategoria_Finale"] = df["Kategoria_Finale"].replace(["", "nan", "0"], "Tjera")

# 3. GRUPIMI FINAL (Për të zvogëluar rreshtat)
print("Duke grupuar dhe kompresuar...")
df_grouped = (
    df.groupby(
        [
            "ForcaShitese",
            "Klienti",
            "Kategoria_Finale",
            "PershkrimiArtikullit",
            "Muaji_Viti",
        ]
    )[["TotalRresht", "kg", "Sasia"]]
    .sum()
    .reset_index()
)

# Krijojmë JSON
json_str = df_grouped.to_json(orient="records")
muajt_disponues = sorted(df["Muaji_Viti"].unique())

print(f"✅ Madhësia e të dhënave u reduktua. Gjenerimi HTML...")

html_content = f"""
<!DOCTYPE html>
<html lang="sq">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Planifikuesi LITE</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --primary: #2563eb; --bg: #f1f5f9; --text: #1e293b; --border: #cbd5e1; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 10px; -webkit-tap-highlight-color: transparent; }}
        .controls {{ background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .header-controls {{ display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }}
        .btn-home {{ background: #f1f5f9; border: 1px solid var(--border); padding: 8px 12px; border-radius: 8px; color: var(--primary); text-decoration: none; display: flex; align-items: center; justify-content: center; }}
        .row {{ display: flex; gap: 10px; margin-bottom: 10px; }}
        select, input {{ width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 1rem; background: #fff; }}
        .btn-run {{ width: 100%; padding: 12px; background: var(--primary); color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 1rem; cursor: pointer; }}
        .global-card {{ background: #1e293b; color: white; border-radius: 12px; padding: 15px; margin-bottom: 20px; }}
        .global-total {{ font-size: 2rem; font-weight: 800; text-align: center; margin: 5px 0 10px 0; color: #4ade80; }}
        .buckets-row {{ display: flex; gap: 8px; margin-bottom: 15px; border-top: 1px solid #334155; padding-top: 15px; }}
        .bucket-box {{ flex: 1; background: #334155; border-radius: 8px; padding: 10px 5px; text-align: right; display: flex; flex-direction: column; justify-content: center; }}
        .bucket-label {{ font-size: 0.65rem; font-weight: bold; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase; }}
        .bucket-val {{ font-size: 0.85rem; font-weight: bold; color: white; }}
        .bucket-box.olim {{ border-bottom: 4px solid #facc15; }}
        .bucket-box.deka {{ border-bottom: 4px solid #38bdf8; }}
        .bucket-box.etj {{ border-bottom: 4px solid #9ca3af; }}
        .global-tabs {{ display: flex; border-bottom: 1px solid #334155; margin-bottom: 10px; }}
        .tab-btn {{ flex: 1; text-align: center; padding: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 600; opacity: 0.6; }}
        .tab-btn.active {{ border-bottom: 2px solid #4ade80; opacity: 1; color: #4ade80; }}
        .global-list {{ max-height: 200px; overflow-y: auto; }}
        .global-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #334155; font-size: 0.85rem; }}
        .agent-card {{ background: white; margin-bottom: 12px; border-radius: 10px; border: 1px solid var(--border); overflow: hidden; }}
        .agent-header {{ padding: 15px; background: #eff6ff; display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-weight: bold; font-size: 1.05rem; color: #1e3a8a; }}
        .agent-body {{ display: none; }}
        .cat-summary {{ background: #fffbeb; padding: 10px; border-bottom: 1px solid #e2e8f0; }}
        .cat-table {{ width: 100%; font-size: 0.85rem; }}
        .cat-table td {{ padding: 3px 0; }}
        .cat-table td:last-child {{ font-weight: bold; text-align: right; }}
        .client-list {{ padding: 0 10px 10px 10px; background: white; }}
        .client-item {{ border-bottom: 1px solid #f1f5f9; }}
        .client-header {{ padding: 12px 5px; display: flex; justify-content: space-between; cursor: pointer; font-weight: 600; font-size: 0.95rem; color: #334155; }}
        .items-container {{ display: none; padding: 5px 10px 15px 10px; background: #f8fafc; border-radius: 6px; margin-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ text-align: left; color: #64748b; font-size: 0.75rem; border-bottom: 1px solid #ccc; }}
        td {{ padding: 6px 0; border-bottom: 1px solid #e2e8f0; }}
        .num {{ text-align: right; font-feature-settings: "tnum"; }}
        .icon-state {{ transition: transform 0.2s; font-size: 0.8rem; color: #64748b; }}
        #loading {{ display: none; text-align: center; padding: 20px; color: var(--primary); font-weight: bold; }}
    </style>
</head>
<body>

    <div class="controls">
        <div class="header-controls">
            <a href="INDEX.html" class="btn-home"><i class="fa-solid fa-house"></i></a>
            <h2 style="margin:0; font-size:1.2rem; color:#1e293b">Planifikuesi LITE</h2>
        </div>
        <div class="row">
            <select id="startMonth"></select>
            <select id="endMonth"></select>
        </div>
        <div class="row">
            <div style="flex:1; position:relative;">
                <input type="number" id="growth" value="10" placeholder="%">
                <span style="position:absolute; right:10px; top:10px; color:#999; font-size:0.8rem; font-weight:bold">% Rritje</span>
            </div>
            <div style="flex:1">
                <select id="metric">
                    <option value="lek">LEK</option>
                    <option value="kg">KG</option>
                    <option value="qty">Cope</option>
                </select>
            </div>
        </div>
        <button class="btn-run" onclick="generatePlan()">Gjenero Planin</button>
    </div>

    <div id="loading"><i class="fa-solid fa-spinner fa-spin"></i> Duke llogaritur...</div>
    <div id="globalArea" style="display:none;"></div>
    <div id="resultsArea"></div>

<script>
// LOAD DATA SAFELY
let rawData = [];
const months = {muajt_disponues};

try {{
    rawData = {json_str};
}} catch(e) {{
    alert("Kujtesa e telefonit plot. Provoni periudha me te shkurtra.");
}}

const startSel = document.getElementById('startMonth');
const endSel = document.getElementById('endMonth');
months.forEach(m => {{ startSel.add(new Option(m, m)); endSel.add(new Option(m, m)); }});
if (months.length > 0) {{
    startSel.value = months[Math.max(0, months.length - 3)];
    endSel.value = months[months.length - 1];
}}

function formatNum(n) {{ if(n >= 1000000) return (n/1000000).toFixed(2) + 'M'; return new Intl.NumberFormat('en-US', {{maximumFractionDigits: 0}}).format(n); }}
function formatFull(n) {{ return new Intl.NumberFormat('en-US', {{maximumFractionDigits: 0}}).format(n); }}
function toggle(id, el) {{ const content = document.getElementById(id); const isOpen = content.style.display === 'block'; content.style.display = isOpen ? 'none' : 'block'; const icon = el.querySelector('.icon-state'); if(icon) icon.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)'; }}
function switchGlobalTab(tab) {{ document.getElementById('tabCat').style.display = tab === 'cat' ? 'block' : 'none'; document.getElementById('tabItem').style.display = tab === 'item' ? 'block' : 'none'; document.getElementById('btnTabCat').classList.toggle('active', tab === 'cat'); document.getElementById('btnTabItem').classList.toggle('active', tab === 'item'); }}
function getMonthDiff(d1Str, d2Str) {{ let d1 = new Date(d1Str + "-01"); let d2 = new Date(d2Str + "-01"); let months = (d2.getFullYear() - d1.getFullYear()) * 12; months -= d1.getMonth(); months += d2.getMonth(); return months <= 0 ? 1 : months + 1; }}

function generatePlan() {{
    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultsArea').innerHTML = '';
    document.getElementById('globalArea').style.display = 'none';

    // Allow UI to update
    setTimeout(() => {{
        const start = startSel.value;
        const end = endSel.value;
        const growth = (parseFloat(document.getElementById('growth').value) || 0) / 100;
        const metric = document.getElementById('metric').value; 

        if (start > end) {{ alert("Muaji fillim > Muaji fund"); document.getElementById('loading').style.display = 'none'; return; }}

        const filtered = rawData.filter(d => d.Muaji_Viti >= start && d.Muaji_Viti <= end);
        const uniqueMonths = getMonthDiff(start, end);

        let tree = {{}};
        let globalCats = {{}};
        let globalItems = {{}};
        let grandTotal = 0;
        let totalOlim = 0;
        let totalEtj = 0;
        let totalDeka = 0;

        filtered.forEach(d => {{
            const agent = d.ForcaShitese;
            const client = d.Klienti;
            const item = d.PershkrimiArtikullit;
            const cat = d.Kategoria_Finale;
            let val = (metric === 'lek') ? d.TotalRresht : (metric === 'kg' ? d.kg : d.Sasia);
            
            if (val > 0) {{
                grandTotal += val;
                let cleanCat = cat.toLowerCase().trim();
                if (cleanCat.includes('vaj') || cleanCat === 'olim') totalOlim += val;
                else if (cleanCat.includes('etj') || cleanCat === 'etj' || cleanCat === 'tjera') totalEtj += val;
                else totalDeka += val;

                if(!globalCats[cat]) globalCats[cat] = 0; globalCats[cat] += val;
                if(!globalItems[item]) globalItems[item] = 0; globalItems[item] += val;

                if(!tree[agent]) tree[agent] = {{ total: 0, cats: {{}}, clients: {{}} }};
                if(!tree[agent].cats[cat]) tree[agent].cats[cat] = 0; tree[agent].cats[cat] += val;
                if(!tree[agent].clients[client]) tree[agent].clients[client] = {{ total: 0, items: {{}} }};
                if(!tree[agent].clients[client].items[item]) tree[agent].clients[client].items[item] = 0;
                tree[agent].clients[client].items[item] += val;
                tree[agent].clients[client].total += val;
                tree[agent].total += val;
            }}
        }});

        const targetGrandTotal = (grandTotal / uniqueMonths) * (1 + growth);
        const targetOlim = (totalOlim / uniqueMonths) * (1 + growth);
        const targetEtj = (totalEtj / uniqueMonths) * (1 + growth);
        const targetDeka = (totalDeka / uniqueMonths) * (1 + growth);

        let globalHtml = `
            <div class="global-card">
                <div class="global-subtitle">OBJEKTIVI TOTAL (PLAN MUJOR)</div>
                <div class="global-total">${{formatFull(targetGrandTotal)}}</div>
                <div style="text-align:center; margin-bottom:15px; font-size:0.75rem; color:#94a3b8">Mesatare e ${{uniqueMonths}} muajve</div>
                <div class="buckets-row">
                    <div class="bucket-box olim"><span class="bucket-label">OLIM (Vaj)</span><span class="bucket-val">${{formatNum(targetOlim)}}</span></div>
                    <div class="bucket-box deka"><span class="bucket-label">DEKA (Detergjentë)</span><span class="bucket-val">${{formatNum(targetDeka)}}</span></div>
                    <div class="bucket-box etj"><span class="bucket-label">ETJ (Të ndryshme)</span><span class="bucket-val">${{formatNum(targetEtj)}}</span></div>
                </div>
                <div class="global-tabs">
                    <div id="btnTabCat" class="tab-btn active" onclick="switchGlobalTab('cat')">Kategoritë</div>
                    <div id="btnTabItem" class="tab-btn" onclick="switchGlobalTab('item')">Artikujt</div>
                </div>
                <div id="tabCat" class="global-list">`;
        Object.entries(globalCats).sort((a,b) => b[1] - a[1]).forEach(([k, v]) => {{ let t = (v / uniqueMonths) * (1 + growth); globalHtml += `<div class="global-row"><span>${{k}}</span><span>${{formatFull(t)}}</span></div>`; }});
        globalHtml += `</div><div id="tabItem" class="global-list" style="display:none;">`;
        Object.entries(globalItems).sort((a,b) => b[1] - a[1]).slice(0, 20).forEach(([k, v]) => {{ let t = (v / uniqueMonths) * (1 + growth); globalHtml += `<div class="global-row"><span>${{k}}</span><span>${{formatFull(t)}}</span></div>`; }});
        globalHtml += `</div></div>`;
        document.getElementById('globalArea').innerHTML = globalHtml;
        document.getElementById('globalArea').style.display = 'block';

        let html = '';
        let agentIndex = 0;
        const sortedAgents = Object.entries(tree).sort((a,b) => b[1].total - a[1].total);
        sortedAgents.forEach(([agentName, agentData]) => {{
            agentIndex++;
            const agentTarget = (agentData.total / uniqueMonths) * (1 + growth);
            const agentId = `agent_${{agentIndex}}`;
            let catHtml = '<table class="cat-table">';
            Object.entries(agentData.cats).sort((a,b) => b[1] - a[1]).forEach(([c, v]) => {{ const t = (v / uniqueMonths) * (1 + growth); if(t > 1) catHtml += `<tr><td>${{c}}</td><td>${{formatFull(t)}}</td></tr>`; }});
            catHtml += '</table>';

            html += `
            <div class="agent-card">
                <div class="agent-header" onclick="toggle('${{agentId}}', this)">
                    <div><i class="fa-solid fa-user-tie"></i> ${{agentName}}</div>
                    <div style="text-align:right"><div>${{formatFull(agentTarget)}}</div></div>
                    <i class="fa-solid fa-chevron-down icon-state" style="margin-left:10px"></i>
                </div>
                <div id="${{agentId}}" class="agent-body">
                    <div class="cat-summary"><span class="cat-title">TOTALET SIPAS KATEGORIVE</span>${{catHtml}}</div>
                    <div class="client-list">`;
            Object.entries(agentData.clients).sort((a,b) => b[1].total - a[1].total).forEach(([clientName, clientData], cIdx) => {{
                const clientTarget = (clientData.total / uniqueMonths) * (1 + growth);
                const clientId = `${{agentId}}_c_${{cIdx}}`;
                if(clientTarget > 1) {{ 
                    html += `
                        <div class="client-item">
                            <div class="client-header" onclick="toggle('${{clientId}}', this)"><span>${{clientName}}</span><span>${{formatFull(clientTarget)}}</span></div>
                            <div id="${{clientId}}" class="items-container">
                                <table><thead><tr><th>Artikulli</th><th class="num">Plan</th></tr></thead><tbody>`;
                    Object.entries(clientData.items).sort((a,b) => b[1] - a[1]).forEach(([item, v]) => {{ const t = (v / uniqueMonths) * (1 + growth); if(t > 0.5) html += `<tr><td>${{item}}</td><td class="num" style="color:#166534; font-weight:bold">${{formatFull(t)}}</td></tr>`; }});
                    html += `</tbody></table></div></div>`;
                }}
            }});
            html += `</div></div></div>`;
        }});

        if (html === '') html = '<div style="text-align:center; padding:20px; color:#666">S’ka të dhëna.</div>';
        document.getElementById('resultsArea').innerHTML = html;
        document.getElementById('loading').style.display = 'none';
    }}, 100);
}}
</script>
</body>
</html>
"""

with open("PLANIFIKIMI_DETAJUAR_V8.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("--- PLANIFIKUESI LITE U KRIJUA! (Zëvendëson origjinalin) ---")
