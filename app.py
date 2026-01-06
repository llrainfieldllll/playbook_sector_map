import streamlit as st
import pandas as pd
import plotly.express as px
from curl_cffi import requests
from datetime import datetime
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="2026 Focus Scanner", layout="wide")

# CSS: Metric Cards Styling
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {font-size: 1.5rem;}
    div[data-testid="stMetricLabel"] {font-weight: bold; font-size: 1rem;}
    .block-container {padding-top: 1rem;}
    div.stButton > button {width: 100%;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. HARDCODED PLAYBOOK ---
PLAYBOOK = {
    "AI Apps & Software": ["PLTR", "ZETA", "APP", "RDDT", "TWLO"],
    "Data Center Components": ["VRT", "MU", "ANET", "CSCO", "COHR", "CRDO", "ALAB"],
    "AI General Chips": ["NVDA", "AMD", "INTC", "KSTR"],
    "AI Mobile Chips": ["ARM", "QCOM", "AAPL"],
    "AI Custom Chips": ["AVGO", "MRVL", "GOOG", "AMZN"],
    "Grid Modernization": ["GEV", "PWR", "GRID", "MTZ", "PAVE"],
    "Data Center Power": ["OKLO", "CEG", "VST", "NEE"],
    "Robotics": ["TSLA", "SYM", "ISRG", "ROBO", "BOTZ"],
    "Nuclear Materials": ["CCJ", "LEU", "UEC", "UUUU"],
    "Precious Metals": ["GLD", "SLV", "CPER", "FCX", "HBM", "PAAS", "NEM"],
    "Healthcare": ["LLY", "VTR", "WELL", "CVS", "MRK"],
    "Auto Sensors": ["ON", "NXPI", "MBLY", "MGA"],
    "International": ["SFTBY", "TOELY", "ITOCY", "PKX", "TSM", "UBS", "BIDU", "BABA"],
    "SpaceX Concepts": ["SATS", "DXYZ", "GOOG", "SMT.L", "ARKVX"],
    "Space Tech": ["LUNR", "RKLB", "ASTS", "PL"],
    "Quantum": ["RGTI", "IONQ", "IBM", "QBTS"],
    "Drones": ["AVAV", "KTOS", "RCAT", "ONDS", "DPRO"]
}
ALL_TICKERS = [t.replace('.', '-') for sublist in PLAYBOOK.values() for t in sublist] + ['SPY']

# --- 3. STEALTH DATA FETCH ---
@st.cache_data(ttl=600)
def fetch_safe_data(tickers):
    session = requests.Session(impersonate="chrome")
    data_map = {}
    progress_bar = st.progress(0)
    unique_tickers = list(set(tickers))
    
    for i, ticker in enumerate(unique_tickers):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=2mo&interval=1d"
            resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                res = resp.json()['chart']['result'][0]
                quotes = res['indicators']['quote'][0]
                timestamps = res['timestamp']
                df = pd.DataFrame({
                    'Date': [datetime.fromtimestamp(ts) for ts in timestamps],
                    'Close': quotes['close'],
                    'Volume': quotes['volume']
                }).dropna()
                if len(df) > 22: data_map[ticker] = df
        except: pass
        if i % 5 == 0: progress_bar.progress((i + 1) / len(unique_tickers))
            
    progress_bar.empty()
    return data_map

# --- 4. ALGORITHM ---
def run_strict_algorithm(data_map):
    sector_results = []
    stock_results = [] # Keep detailed stock data separate
    
    spy = data_map.get('SPY')
    if spy is None: return pd.DataFrame(), pd.DataFrame()
    
    spy_today_date = spy['Date'].iloc[-1].date()
    spy_change = (spy['Close'].iloc[-1] - spy['Close'].iloc[-2]) / spy['Close'].iloc[-2] * 100

    for sector, tickers in PLAYBOOK.items():
        sector_stock_data = []
        green_stocks = 0
        total_stocks = 0
        
        for t in tickers:
            clean_t = t.replace('.', '-')
            df = data_map.get(clean_t)
            if df is None: continue
            if df['Date'].iloc[-1].date() != spy_today_date: continue 
            
            total_stocks += 1
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            change_pct = (curr['Close'] - prev['Close']) / prev['Close'] * 100
            if change_pct > 0: green_stocks += 1
            
            alpha_val = change_pct - spy_change
            avg_vol = df['Volume'].iloc[-22:-2].mean()
            rvol = curr['Volume'] / avg_vol if avg_vol > 0 else 0
            sma20 = df['Close'].iloc[-21:-1].mean()
            price_above_ma = curr['Close'] > sma20
            
            # Stock Detail Record
            stock_results.append({
                'Sector': sector,
                'Ticker': t,
                'Price': curr['Close'],
                'Change %': change_pct,
                'RVol': rvol,
                'Above MA': price_above_ma
            })
            
            sector_stock_data.append({
                'Alpha': alpha_val, 'RVol': rvol, 'Above_MA': price_above_ma
            })
            
        if total_stocks > 0:
            avg_alpha = sum(d['Alpha'] for d in sector_stock_data) / total_stocks
            avg_rvol = sum(d['RVol'] for d in sector_stock_data) / total_stocks
            avg_trend = sum(d['Above_MA'] for d in sector_stock_data) / total_stocks
            pct_green = green_stocks / total_stocks
            
            score = 0
            if avg_alpha > 0: score += 40
            if avg_rvol > 1.10: score += 30
            if avg_trend > 0.5: score += 20
            if pct_green > 0.5: score += 10
            
            # Hard Gate
            if pct_green <= 0.5: score = min(score, 59)
                
            sector_results.append({
                'Sector': sector,
                'Heat Score': score,
                'Size': 1, # Equal Size Blocks
                'Stocks Count': total_stocks
            })

    return pd.DataFrame(sector_results), pd.DataFrame(stock_results)

# --- 5. UI ---
st.title("🦅 2026 Focus Scanner")

if st.button("🚀 RUN FOCUS SCAN", type="primary"):
    with st.spinner("Analyzing Market..."):
        data = fetch_safe_data(ALL_TICKERS)
        df_sectors, df_stocks = run_strict_algorithm(data)
    
    if not df_sectors.empty:
        # --- A. MACRO MAP (Clean Sectors Only) ---
        st.subheader("1. Macro View (Sectors)")
        
        fig = px.treemap(
            df_sectors,
            path=[px.Constant("Market"), 'Sector'], # No Ticker nesting
            values='Size',
            color='Heat Score',
            color_continuous_scale=['#FF4B4B', '#262730', '#00FF00'], 
            range_color=[0, 100],
            title=""
        )
        fig.update_traces(textinfo="label", textfont=dict(size=18))
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # --- B. SECTOR INSPECTOR (The Detail View) ---
        st.divider()
        st.subheader("2. Sector Inspector")
        
        # Find the hottest sector to default to
        hottest_sector = df_sectors.sort_values('Heat Score', ascending=False).iloc[0]['Sector']
        
        # Dropdown to pick sector
        selected_sector = st.selectbox("Inspect Sector:", df_sectors['Sector'].unique(), index=list(df_sectors['Sector']).index(hottest_sector))
        
        # Filter stocks for that sector
        sector_stocks = df_stocks[df_stocks['Sector'] == selected_sector].sort_values('RVol', ascending=False)
        
        # Display as clean Metric Cards
        st.caption(f"Showing stocks inside **{selected_sector}** sorted by Volume Conviction.")
        
        # Grid Layout for stocks
        cols = st.columns(4)
        for i, (idx, row) in enumerate(sector_stocks.iterrows()):
            col_idx = i % 4
            with cols[col_idx]:
                # Color code the metric
                color = "normal"
                if row['Change %'] > 0: color = "normal" # Streamlit handles green automatically for positive delta
                
                st.metric(
                    label=row['Ticker'],
                    value=f"${row['Price']:.2f}",
                    delta=f"{row['Change %']:.2f}% (Vol: {row['RVol']:.1f}x)"
                )
                
    else:
        st.error("Connection Failed. Try again.")
