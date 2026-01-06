import streamlit as st
import pandas as pd
import plotly.express as px
from curl_cffi import requests
from datetime import datetime
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="2026 Focus Scanner", layout="wide")

# ADHD-Optimized CSS: Bigger fonts, clearer labels to reduce eye strain
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    div[data-testid="stMetricLabel"] {font-weight: bold;}
    .block-container {padding-top: 2rem;}
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
# Flatten for efficient fetching
ALL_TICKERS = [t.replace('.', '-') for sublist in PLAYBOOK.values() for t in sublist] + ['SPY']

# --- 3. RED TEAM MODULE: STEALTH DATA FETCH ---
@st.cache_data(ttl=600)
def fetch_safe_data(tickers):
    """
    Fetches market data using browser impersonation to avoid 403 errors.
    """
    session = requests.Session(impersonate="chrome")
    data_map = {}
    
    # Progress Bar (Visual Feedback for ADHD impatience)
    progress_bar = st.progress(0)
    unique_tickers = list(set(tickers))
    
    for i, ticker in enumerate(unique_tickers):
        try:
            # Fetch 2 months of data to ensure valid Moving Averages
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
                
                # Validation: Need at least 22 days for the algorithm
                if len(df) > 22:
                    data_map[ticker] = df
                    
        except Exception:
            pass # Skip individual failures to keep the app running
            
        # Update progress bar sparingly
        if i % 5 == 0:
            progress_bar.progress((i + 1) / len(unique_tickers))
            
    progress_bar.empty()
    return data_map

# --- 4. RED TEAM MODULE: ALGORITHM (HARD GATE) ---
def run_strict_algorithm(data_map):
    results = []
    
    # 1. Benchmark (SPY) Logic & Date Sync
    spy = data_map.get('SPY')
    if spy is None: return pd.DataFrame()
    
    # Capture SPY Date to prevent "Stale Data" trades
    spy_today_date = spy['Date'].iloc[-1].date()
    spy_change = (spy['Close'].iloc[-1] - spy['Close'].iloc[-2]) / spy['Close'].iloc[-2] * 100

    for sector, tickers in PLAYBOOK.items():
        sector_scores = []
        green_stocks = 0
        total_stocks = 0
        
        for t in tickers:
            clean_t = t.replace('.', '-')
            df = data_map.get(clean_t)
            if df is None: continue
            
            # --- CRITICAL SAFETY CHECK: DATE ALIGNMENT ---
            # If stock data is old (e.g., halted or delayed), DO NOT use it.
            stock_date = df['Date'].iloc[-1].date()
            if stock_date != spy_today_date:
                continue 
            
            total_stocks += 1
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- METRICS CALCULATION ---
            # 1. Price Change
            change_pct = (curr['Close'] - prev['Close']) / prev['Close'] * 100
            if change_pct > 0: green_stocks += 1
            
            # 2. Alpha (Stock vs SPY)
            alpha_val = change_pct - spy_change
            
            # 3. Relative Volume (vs previous 20 days)
            avg_vol = df['Volume'].iloc[-22:-2].mean()
            rvol = curr['Volume'] / avg_vol if avg_vol > 0 else 0
            
            # 4. Trend (Above MA20)
            sma20 = df['Close'].iloc[-21:-1].mean()
            price_above_ma = curr['Close'] > sma20
            
            # --- INDIVIDUAL STOCK SCORE (0-100) ---
            # Used for the coloring of the small boxes in the nested grid
            stock_score = 0
            if alpha_val > 0: stock_score += 40
            if rvol > 1.10: stock_score += 30
            if price_above_ma: stock_score += 20
            if change_pct > 0: stock_score += 10
            
            sector_scores.append({
                'Ticker': t,
                'Alpha': alpha_val,
                'RVol': rvol,
                'Above_MA': price_above_ma,
                'Heat Score': stock_score,
                'Change %': change_pct,
                'Price': curr['Close'],
                'Size': 1 # Equal weighting for visualization
            })
            
        if total_stocks > 0:
            # --- SECTOR SCORING (THE 0-100 FORMULA) ---
            avg_alpha = sum(d['Alpha'] for d in sector_scores) / total_stocks
            avg_rvol = sum(d['RVol'] for d in sector_scores) / total_stocks
            avg_trend = sum(d['Above_MA'] for d in sector_scores) / total_stocks
            pct_green = green_stocks / total_stocks
            
            score = 0
            if avg_alpha > 0: score += 40      # Market Alpha
            if avg_rvol > 1.10: score += 30    # Volume Conviction
            if avg_trend > 0.5: score += 20    # Trend Integrity
            if pct_green > 0.5: score += 10    # Breadth Bonus
            
            # --- CRITICAL SAFETY CHECK: THE HARD GATE ---
            # If Breadth < 50%, CAP the score at 59 (Grey).
            # This prevents a "Fake Sector" (1 stock rallying) from turning Green.
            if pct_green <= 0.5:
                score = min(score, 59)
                
            # Add to results (Flattened for Treemap)
            for s in sector_scores:
                results.append({
                    'Sector': sector,
                    'Ticker': s['Ticker'],
                    'Heat Score': score,       # Parent Sector Color
                    'Stock Score': s['Heat Score'], # Child Stock Color
                    'RVol': s['RVol'],
                    'Change %': s['Change %'],
                    'Price': s['Price'],
                    'Size': 1
                })

    return pd.DataFrame(results)

# --- 5. ADHD FOCUS UI ---
st.title("🦅 2026 Focus Scanner")

if st.button("🚀 RUN FOCUS SCAN", type="primary", use_container_width=True):
    
    with st.spinner("Analyzing Market Breadth & Volume..."):
        data = fetch_safe_data(ALL_TICKERS)
        df = run_strict_algorithm(data)
    
    if not df.empty:
        # --- A. BIG BANNER (Eliminate Ambiguity) ---
        # "Passing" Sector = Score >= 60 (Healthy)
        # We group by sector to count unique sectors passing
        unique_sectors = df.groupby('Sector')['Heat Score'].first()
        passing_sectors = len(unique_sectors[unique_sectors >= 60])
        total_sectors = len(unique_sectors)
        ratio = passing_sectors / total_sectors
        
        if ratio > 0.5:
            st.success(f"🟢 MARKET STATUS: BULLISH ({ratio:.0%} Sectors Green)")
        elif ratio > 0.3:
            st.warning(f"🟡 MARKET STATUS: CHOPPY ({ratio:.0%} Sectors Green)")
        else:
            st.error(f"🔴 MARKET STATUS: DEFENSIVE ({ratio:.0%} Sectors Green)")

        # --- B. NESTED HEATMAP (Visual Hierarchy) ---
        # Path: Market -> Sector -> Ticker
        # This shows the Sector color primarily, but lets you see the Stocks inside.
        fig = px.treemap(
            df,
            path=[px.Constant("Market"), 'Sector', 'Ticker'],
            values='Size',
            color='Heat Score', # Color based on SECTOR Score (The Hard Gated Score)
            color_continuous_scale=['#FF4B4B', '#262730', '#00FF00'], 
            range_color=[0, 100],
            hover_data=['RVol', 'Change %', 'Price'],
            title="Market Matrix (Zoomable)"
        )
        
        # UI Tweak: Show Ticker Label and Value
        fig.update_traces(textinfo="label+value")
        fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # --- C. THE "RULE OF 3" SNIPER LIST ---
        st.divider()
        st.subheader("🎯 Top 3 High-Conviction Setups")
        st.caption("Stocks in **Green Sectors** with **>1.2x Volume**. Ignore the rest.")
        
        # Filter Logic:
        # 1. Sector Score must be >= 80 (Confirmed Trend)
        # 2. Individual Stock RVol must be > 1.2 (Institutional Activity)
        top_picks = df[
            (df['Heat Score'] >= 80) & 
            (df['RVol'] > 1.2)
        ].sort_values('RVol', ascending=False).head(3)
        
        if not top_picks.empty:
            cols = st.columns(3)
            for i, (idx, row) in enumerate(top_picks.iterrows()):
                with cols[i]:
                    st.metric(
                        label=f"{row['Ticker']} ({row['Sector']})",
                        value=f"${row['Price']:.2f}",
                        delta=f"Vol: {row['RVol']:.1f}x"
                    )
        else:
            st.info("💤 No High-Conviction Setups Found. Cash is a position.")

    else:
        st.error("Connection Failed. Market may be closed or data blocked.")
