import streamlit as st
import pandas as pd
import plotly.express as px
from curl_cffi import requests
from datetime import datetime
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="2026 Focus Scanner", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {font-size: 1.5rem;}
    div[data-testid="stMetricLabel"] {font-weight: bold; font-size: 1rem;}
    .block-container {padding-top: 1rem;}
    div.stButton > button {width: 100%;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. PLAYBOOK ---
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

# --- 3. ROBUST DATA FETCHING ---
@st.cache_data(ttl=600)
def fetch_safe_data(tickers):
    session = requests.Session(impersonate="chrome")
    data_map = {}
    progress_bar = st.progress(0)
    unique_tickers = list(set(tickers))
    
    # Track failures for Red Team auditing
    fail_count = 0
    
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
                
                # Validation: Need sufficient data for Moving Averages
                if len(df) > 22: 
                    data_map[ticker] = df
                else:
                    fail_count += 1
            else:
                fail_count += 1
                
        except Exception:
            fail_count += 1
            pass
        
        if i % 5 == 0: 
            progress_bar.progress((i + 1) / len(unique_tickers))
            
    progress_bar.empty()
    
    # Red Team Warning: If >50% failed, alert the user
    if fail_count > (len(unique_tickers) / 2):
        st.toast(f"⚠️ Warning: {fail_count} tickers failed to load. Data source may be unstable.", icon="⚠️")
        
    return data_map

# --- 4. LOGIC ALGORITHM ---
def run_strict_algorithm(data_map):
    sector_results = []
    stock_results = []
    
    # --- RED TEAM FIX #1: SPY SOFT FAIL ---
    spy = data_map.get('SPY')
    if spy is None:
        st.error("⚠️ SPY (Benchmark) failed to load. 'Alpha' scores will be inaccurate.")
        spy_change = 0.0 # Default to 0 so the app doesn't crash
        spy_today_date = datetime.now().date() # Fallback date
    else:
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
            
            # Date Alignment Check (skip stale data)
            if spy is not None and df['Date'].iloc[-1].date() != spy_today_date: 
                continue 
            
            total_stocks += 1
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            change_pct = (curr['Close'] - prev['Close']) / prev['Close'] * 100
            if change_pct > 0: green_stocks += 1
            
            alpha_val = change_pct - spy_change
            
            # --- SENIOR DEV FIX #1: CORRECT VOLUME SLICE ---
            # Old: [-22:-2] (Ignored yesterday)
            # New: [-21:-1] (Includes yesterday, excludes today)
            avg_vol = df['Volume'].iloc[-21:-1].mean()
            rvol = curr['Volume'] / avg_vol if avg_vol > 0 else 0
            
            sma20 = df['Close'].iloc[-21:-1].mean()
            price_above_ma = curr['Close'] > sma20
            
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
            
            if pct_green <= 0.5: score = min(score, 59)
                
            sector_results.append({
                'Sector': sector,
                'Heat Score': score,
                'Size': 1,
                'Stocks Count': total_stocks
            })

    return pd.DataFrame(sector_results), pd.DataFrame(stock_results)

# --- 5. UI (WITH TIMESTAMP) ---
st.title("🦅 2026 Focus Scanner")

# Initialize Session State
if 'scan_data' not in st.session_state:
    st.session_state.scan_data = None
if 'stocks_data' not in st.session_state:
    st.session_state.stocks_data = None
if 'scan_time' not in st.session_state:
    st.session_state.scan_time = None

if st.button("🚀 RUN FOCUS SCAN", type="primary"):
    with st.spinner("Analyzing Market..."):
        data = fetch_safe_data(ALL_TICKERS)
        df_sectors, df_stocks = run_strict_algorithm(data)
        
        st.session_state.scan_data = df_sectors
        st.session_state.stocks_data = df_stocks
        # --- SENIOR DEV FIX #2: SAVE TIMESTAMP ---
        st.session_state.scan_time = datetime.now().strftime("%H:%M")

if st.session_state.scan_data is not None and not st.session_state.scan_data.empty:
    
    df_sectors = st.session_state.scan_data
    df_stocks = st.session_state.stocks_data
    
    # Display Timestamp
    st.caption(f"Last Scanned: {st.session_state.scan_time} (Click Run to Refresh)")
    
    # --- A. MACRO MAP ---
    st.subheader("1. Macro View (Sectors)")
    fig = px.treemap(
        df_sectors,
        path=[px.Constant("Market"), 'Sector'],
        values='Size',
        color='Heat Score',
        color_continuous_scale=['#FF4B4B', '#262730', '#00FF00'], 
        range_color=[0, 100],
        title=""
    )
    fig.update_traces(textinfo="label", textfont=dict(size=18))
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # --- B. SECTOR INSPECTOR ---
    st.divider()
    st.subheader("2. Sector Inspector")
    
    hottest_sector = df_sectors.sort_values('Heat Score', ascending=False).iloc[0]['Sector']
    
    selected_sector = st.selectbox(
        "Inspect Sector:", 
        df_sectors['Sector'].unique(), 
        index=list(df_sectors['Sector']).index(hottest_sector)
    )
    
    sector_stocks = df_stocks[df_stocks['Sector'] == selected_sector].sort_values('RVol', ascending=False)
    
    st.caption(f"Showing stocks inside **{selected_sector}** sorted by Volume Conviction.")
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(sector_stocks.iterrows()):
        col_idx = i % 4
        with cols[col_idx]:
            st.metric(
                label=row['Ticker'],
                value=f"${row['Price']:.2f}",
                delta=f"{row['Change %']:.2f}% (Vol: {row['RVol']:.1f}x)"
            )

elif st.session_state.scan_data is not None and st.session_state.scan_data.empty:
    st.error("Connection Failed. No data returned from source.")
