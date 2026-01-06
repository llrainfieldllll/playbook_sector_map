import streamlit as st
import pandas as pd
import plotly.express as px
from curl_cffi import requests
from datetime import datetime
import time

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="2026 Focus Scanner", layout="wide")

# Custom CSS for ADHD Focus (Cleaner Metrics)
st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {font-size: 1.8rem;}
    div[data-testid="stMetricLabel"] {font-weight: bold;}
    .block-container {padding-top: 2rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. HARDCODED PLAYBOOK (Instant Load) ---
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
# Flatten for fetching
ALL_TICKERS = [t.replace('.', '-') for sublist in PLAYBOOK.values() for t in sublist] + ['SPY']

# --- 3. RED TEAM MODULE: STEALTH FETCH & VALIDATION ---
@st.cache_data(ttl=600)
def fetch_safe_data(tickers):
    """
    Implements 'Finding 2': Downloads last 5 days to ensure valid session data.
    Uses curl_cffi to bypass Yahoo 403 blocks.
    """
    session = requests.Session(impersonate="chrome")
    data_map = {}
    
    unique_tickers = list(set(tickers))
    
    # Progress Bar for User Feedback
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(unique_tickers):
        try:
            # Fetch 2 months for MA20 calculation
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
                
                # Validation: Must have at least 22 days of data for MA20
                if not df.empty and len(df) > 22:
                    data_map[ticker] = df
                    
        except Exception:
            pass # Fail silently for individual stocks
        
        # Update progress every 5 tickers to save redraws
        if i % 5 == 0:
            progress_bar.progress((i + 1) / len(unique_tickers))
            
    progress_bar.empty()
    return data_map

# --- 4. RED TEAM MODULE: EXACT SCORING FORMULA ---
def run_strict_algorithm(data_map):
    results = []
    
    # Benchmark (SPY) Logic
    spy = data_map.get('SPY')
    if spy is None: return pd.DataFrame()
    spy_today = spy.iloc[-1]
    spy_prev = spy.iloc[-2]
    spy_change = (spy_today['Close'] - spy_prev['Close']) / spy_prev['Close'] * 100

    for sector, tickers in PLAYBOOK.items():
        sector_scores = []
        green_stocks = 0
        total_stocks = 0
        
        for t in tickers:
            clean_t = t.replace('.', '-')
            df = data_map.get(clean_t)
            if df is None: continue
            
            total_stocks += 1
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Metric 1: Price Change
            change_pct = (curr['Close'] - prev['Close']) / prev['Close'] * 100
            if change_pct > 0: green_stocks += 1
            
            # Metric 2: Alpha (Stock vs SPY)
            alpha_val = change_pct - spy_change
            
            # Metric 3: Relative Volume (vs 20 Day Avg)
            # Strict logic: Avg of previous 20 days (excluding today)
            avg_vol = df['Volume'].iloc[-22:-2].mean()
            rvol = curr['Volume'] / avg_vol if avg_vol > 0 else 0
            
            # Metric 4: Trend (Above MA20)
            sma20 = df['Close'].iloc[-21:-1].mean()
            price_above_ma = curr['Close'] > sma20
            
            sector_scores.append({
                'Ticker': t,
                'Alpha': alpha_val,
                'RVol': rvol,
                'Above_MA': price_above_ma,
                'Change %': change_pct
            })
            
        if total_stocks > 0:
            # --- SECTOR LEVEL AGGREGATION ---
            avg_alpha = sum(d['Alpha'] for d in sector_scores) / total_stocks
            avg_rvol = sum(d['RVol'] for d in sector_scores) / total_stocks
            avg_trend = sum(d['Above_MA'] for d in sector_scores) / total_stocks
            pct_green = green_stocks / total_stocks
            
            # --- THE EXACT SCORECARD (0-100) [Cite: Red Team Doc] ---
            score = 0
            
            # 1. Market Alpha (40%): Did Sector Outperform SPY?
            # We use avg_alpha (Sector Avg Return - SPY Return)
            if avg_alpha > 0: score += 40
            
            # 2. Volume Surge (30%): Is Avg RVol > 1.10?
            if avg_rvol > 1.10: score += 30
            
            # 3. Trend Integrity (20%): Are >50% of stocks above MA20?
            if avg_trend > 0.5: score += 20
            
            # 4. Breadth Bonus (10%): Are >50% of stocks Green?
            if pct_green > 0.5: score += 10
            
            results.append({
                'Sector': sector,
                'Heat Score': score,
                'RVol': avg_rvol,
                'Alpha': avg_alpha,
                'Breadth': pct_green,
                'Stocks': total_stocks
            })

    return pd.DataFrame(results)

# --- 5. ADHD EXPERT UI: FOCUS MODE ---
st.title("🦅 2026 Focus Scanner")

# The "One Click" Action
if st.button("🚀 RUN FOCUS SCAN", type="primary", use_container_width=True):
    
    with st.spinner("Processing Market Data..."):
        data = fetch_safe_data(ALL_TICKERS)
        df = run_strict_algorithm(data)
    
    if not df.empty:
        # --- A. BIG BANNER (Eliminate Ambiguity) ---
        # "Passing" = Score >= 60 (Healthy Sector)
        passing_sectors = len(df[df['Heat Score'] >= 60])
        total_sectors = len(df)
        market_health = passing_sectors / total_sectors
        
        if market_health > 0.5:
            st.success(f"🟢 MARKET STATUS: BULLISH ({passing_sectors}/{total_sectors} Sectors Green)")
        elif market_health > 0.3:
            st.warning(f"🟡 MARKET STATUS: CHOPPY ({passing_sectors}/{total_sectors} Sectors Green)")
        else:
            st.error(f"🔴 MARKET STATUS: DEFENSIVE ({passing_sectors}/{total_sectors} Sectors Green)")

        # --- B. VISUAL HEATMAP ---
        # Color Scale: Red (0-40), Grey (50-70), Green (80-100)
        fig = px.treemap(
            df,
            path=[px.Constant("Market"), 'Sector'],
            values='Stocks',
            color='Heat Score',
            color_continuous_scale=['#FF4B4B', '#262730', '#00FF00'], 
            range_color=[0, 100],
            title="Money Flow Matrix (Size = Stock Count)"
        )
        fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # --- C. THE "RULE OF 3" SNIPER LIST ---
        st.divider()
        st.subheader("🎯 Top 3 High-Conviction Setups")
        st.caption("Stocks in Sectors with **Score >= 80** (Alpha + Volume + Trend confirmed).")
        
        # Filter: High Score Sectors -> Sort by RVol -> Take Top 3
        # We need to re-find the top tickers corresponding to high-score sectors
        high_score_sectors = df[df['Heat Score'] >= 80]['Sector'].tolist()
        
        # Create a display list
        top_picks = []
        for sector in high_score_sectors:
            tickers = PLAYBOOK[sector]
            for t in tickers:
                clean_t = t.replace('.', '-')
                stock_df = data.get(clean_t)
                if stock_df is None: continue
                
                # Recalculate stock-specific metrics for the list
                curr = stock_df.iloc[-1]
                avg_vol = stock_df['Volume'].iloc[-22:-2].mean()
                rvol = curr['Volume'] / avg_vol if avg_vol > 0 else 0
                
                # Only show stocks with High RVol inside the High Score Sector
                if rvol > 1.2:
                    top_picks.append({
                        'Sector': sector,
                        'Ticker': t,
                        'RVol': rvol,
                        'Price': curr['Close']
                    })
        
        # Sort by RVol and take TOP 3
        top_3 = sorted(top_picks, key=lambda x: x['RVol'], reverse=True)[:3]
        
        if top_3:
            cols = st.columns(3)
            for i, pick in enumerate(top_3):
                with cols[i]:
                    st.metric(
                        label=f"{pick['Ticker']} ({pick['Sector']})",
                        value=f"${pick['Price']:.2f}",
                        delta=f"Vol: {pick['RVol']:.1f}x Avg"
                    )
        else:
            st.info("💤 No stocks met the 'Sniper' criteria (>1.2x Volume in >80 Score Sector). Cash is a position.")
            
    else:
        st.error("Data fetch failed. Market may be closed or connection blocked.")
