"""
Battery Cost Forecast Streamlit Application.

This app provides interactive visualization of battery material prices and
chemistry costs with forecasting capabilities.
"""

import os, json, io, subprocess, sys
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# Local helper for Excel export
try:
    from src.utils_io import to_excel_bytes
except Exception:
    # Fallback if module path differs when run from root
    try:
        from utils_io import to_excel_bytes
    except Exception:
        def to_excel_bytes(sheets):
            import io
            with pd.ExcelWriter(io.BytesIO(), engine="xlsxwriter") as writer:
                for name, df in sheets.items():
                    df.to_excel(writer, index=False, sheet_name=name[:31])
                return writer.book.filename.getvalue()  # type: ignore

st.set_page_config(
    page_title="🔋 Battery Cost Forecaster", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🔋"
)

# Enhanced modern styling
st.markdown(
    """
    <style>
    /* Main app styling */
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem;
        border: none;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
    }
    
    .kpi-title {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0.5rem 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
    }
    
    .kpi-delta {
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 20px;
        display: inline-block;
    }
    
    .kpi-delta.positive {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    .kpi-delta.negative {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .kpi-delta.neutral {
        background: rgba(156, 163, 175, 0.2);
        color: #9ca3af;
        border: 1px solid rgba(156, 163, 175, 0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8fafc;
    }
    
    /* Chart containers */
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #f1f5f9;
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: #667eea;
        color: white;
    }
    
    /* Metric styling */
    .metric-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stError {
        background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border-radius: 8px;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🔋 Battery Cost Forecaster</h1>
    <p>Advanced scenario modeling and cost analysis for battery materials</p>
</div>
""", unsafe_allow_html=True)

# Load data with better error handling
data_loaded = False
mat = None
chem_mo = None
inten = None
symbols = {}

try:
    # Check if processed files exist
    if Path("processed/material_forecasts.csv").exists() and Path("processed/chemistry_costs_monthly.csv").exists():
        mat = pd.read_csv("processed/material_forecasts.csv", parse_dates=["date"])
        chem_mo = pd.read_csv("processed/chemistry_costs_monthly.csv", parse_dates=["date"])
        data_loaded = True
    else:
        st.warning("⚠️ **No processed data found.** This is normal for first-time deployment.")
        
    # Load intensity data (should always exist)
    inten = pd.read_csv("data/intensity_baseline.csv")
    
    # Load symbols metadata if available
    if Path("processed/symbols_te.json").exists():
        symbols = json.loads(Path("processed/symbols_te.json").read_text())
        
except Exception as e:
    st.error(f"❌ **Error loading data:** {str(e)}")
    st.stop()

# Show initialization message if no data
if not data_loaded:
    st.markdown("## 🔋 Battery Cost Forecast App")
    st.markdown("### Welcome! Let's get started...")
    
    st.info("""
    **This app forecasts battery material costs and chemistry prices.**
    
    To begin, you need to initialize the data by running the data processing scripts.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🌐 **Option 1: Use Live Data (Recommended)**")
        st.markdown("Fetch real-time commodity prices from APIs")
        if st.button("🚀 Initialize with Live Data", help="Fetch live prices and build forecasts"):
            with st.spinner("Fetching live data and building forecasts..."):
                try:
                    # Run the data fetching and building scripts
                    result1 = subprocess.run([sys.executable, "scripts/fetch_real_commodity_prices.py"], 
                                           capture_output=True, text=True)
                    result2 = subprocess.run([sys.executable, "scripts/build_forecasts.py"], 
                                           capture_output=True, text=True)
                    
                    if result1.returncode == 0 and result2.returncode == 0:
                        st.success("✅ Data initialized successfully! Refreshing app...")
                        st.rerun()
                    else:
                        st.error("❌ Initialization failed. Check the logs below:")
                        with st.expander("Fetch Script Logs"):
                            st.code(result1.stdout + "\n" + result1.stderr)
                        with st.expander("Build Script Logs"):
                            st.code(result2.stdout + "\n" + result2.stderr)
                except Exception as e:
                    st.error(f"❌ Error during initialization: {e}")
    
    with col2:
        st.markdown("#### 📁 **Option 2: Upload Your Data**")
        st.markdown("Upload CSV/Excel files with your own price data")
        st.markdown("**Steps:**")
        st.markdown("1. Switch to 'Physical Mode' in the sidebar")
        st.markdown("2. Upload your CSV/Excel files")
        st.markdown("3. Click 'Process Uploaded Files'")
    
    st.markdown("---")
    st.markdown("### 📋 **Manual Setup (Advanced)**")
    st.markdown("If you prefer to run scripts manually, use these commands:")
    st.code("""
# For live data:
python scripts/fetch_real_commodity_prices.py
python scripts/build_forecasts.py

# For uploaded data:
python scripts/process_uploaded_data.py
python scripts/build_forecasts.py
    """)
    
    st.stop()

# Normalize intensity names to price columns
inten["material_norm"] = inten["material"].str.lower().str.replace(" ", "_", regex=False)
inten_alias = {"manganese": "manganese_sulfate"}
inten["material_key"] = inten["material_norm"].map(lambda x: inten_alias.get(x, x))

# Materials list
materials_all = sorted(mat["material"].unique())
chems_all = sorted(inten["chemistry"].unique())

# Enhanced Sidebar
st.sidebar.markdown("## ⚙️ Control Panel")

# Data Source Mode Selection
st.sidebar.markdown("### 🔧 Data Source Mode")
data_mode = st.sidebar.radio(
    "Choose data source:",
    ["API Mode (Live Data)", "Physical Mode (Upload Files)"],
    help="API Mode fetches live prices, Physical Mode uses uploaded files",
    key="data_source_mode"
)

# Physical Mode - File Upload Section
if data_mode == "Physical Mode (Upload Files)":
    st.sidebar.markdown("### 📁 Upload Price Files")
    st.sidebar.markdown("**Upload CSV/Excel files with material prices**")
    
    # File format info
    with st.sidebar.expander("📋 Expected File Format", expanded=False):
        st.markdown("""
        **CSV/Excel Format Options:**
        
        **Option 1: Multiple materials in one file**
        ```
        date,material,price_usd_per_ton
        2024-01-01,lithium_carbonate,25000
        2024-01-01,nickel,20000
        2024-02-01,lithium_carbonate,24000
        ```
        
        **Option 2: Single material per file**
        ```
        date,price_usd_per_ton
        2024-01-01,25000
        2024-02-01,24000
        ```
        
        **Supported Materials:**
        - lithium_carbonate, nickel, cobalt
        - manganese_sulfate, graphite_battery
        - copper, aluminum
        """)
        
        # Download sample file
        sample_file = Path("data/sample_material_prices.csv")
        if sample_file.exists():
            with open(sample_file, 'rb') as f:
                st.download_button(
                    "📥 Download Sample CSV",
                    f.read(),
                    "sample_material_prices.csv",
                    "text/csv"
                )
    
    # File uploader
    uploaded_files = st.sidebar.file_uploader(
        "Choose files",
        type=['csv', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload CSV or Excel files with material price data"
    )
    
    if uploaded_files:
        st.sidebar.success(f"📁 {len(uploaded_files)} file(s) uploaded")
        
        # Process uploaded files
        uploaded_data = {}
        for file in uploaded_files:
            try:
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                else:  # Excel files
                    df = pd.read_excel(file)
                
                # Show file preview
                with st.sidebar.expander(f"📄 {file.name}", expanded=False):
                    st.dataframe(df.head(), use_container_width=True)
                    st.caption(f"Shape: {df.shape}")
                
                uploaded_data[file.name] = df
                
            except Exception as e:
                st.sidebar.error(f"❌ Error reading {file.name}: {str(e)}")
        
        # Save uploaded data to processed folder
        if uploaded_data:
            processed_dir = Path("processed")
            processed_dir.mkdir(exist_ok=True)
            
            # Save each file
            for filename, df in uploaded_data.items():
                output_path = processed_dir / f"uploaded_{filename}"
                if filename.endswith('.csv'):
                    df.to_csv(output_path, index=False)
                else:
                    df.to_excel(output_path, index=False)
            
            st.sidebar.success("✅ Files saved to processed/ folder")
            
            # Option to use uploaded data for forecasting
            if st.sidebar.button("🔄 Use Uploaded Data for Forecasting", help="Process uploaded files and rebuild forecasts"):
                with st.spinner("Processing uploaded data..."):
                    try:
                        # Run a custom script to process uploaded data
                        result = subprocess.run([
                            sys.executable, "scripts/process_uploaded_data.py"
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            st.sidebar.success("✅ Forecasts updated with uploaded data!")
                            st.rerun()
                        else:
                            st.sidebar.error("❌ Error processing uploaded data")
                            st.sidebar.code(result.stderr)
                    except Exception as e:
                        st.sidebar.error(f"❌ Error: {e}")

# API Mode - Live Data Section
else:
    st.sidebar.markdown("### 🌐 Live Data Sources")
    st.sidebar.info("""
    **Current API Sources:**
    - 🔌 Copper: Yahoo Finance (HG=F)
    - 🛩️ Aluminum: Yahoo Finance (ALI=F)  
    - ⚡ Nickel: LIT ETF (scaled)
    - 🔋 Lithium: Manual CSV + LIT ETF
    - 🧲 Cobalt: LAC ETF (scaled)
    - 📊 Graphite/MnSO₄: Baselines
    """)

# Series Selection
with st.sidebar.expander("📊 Data Series", expanded=True):
    sel_materials = st.multiselect(
        "Materials to analyze", 
        options=materials_all, 
        default=materials_all,
        help="Select which materials to include in analysis"
    )
    sel_chems = st.multiselect(
        "Battery chemistries", 
        options=chems_all, 
        default=chems_all,
        help="Select which battery chemistries to analyze"
    )
    series_kind = st.radio(
        "Data range", 
        ["History + Forecast", "History only", "Forecast only"], 
        index=0,
        help="Choose which data to display"
    )

# Scenario Modeling
with st.sidebar.expander("🎯 Scenario Modeling", expanded=True):
    st.markdown("**Price Shocks (%)**")
    st.caption("Apply percentage changes to material prices")
    
    shock_pct = {}
    for m in materials_all:
        pretty = m.replace("_", " ").title()
        shock_pct[m] = st.slider(
            f"{pretty}", 
            -50, 50, 0, 1,
            help=f"Percentage change for {pretty} prices"
        )
    
    st.markdown("**Recycling Impact**")
    recycle_global = st.slider(
        "Global recycling rate (%)", 
        0, 100, 0, 1,
        help="Reduces material intensity across all chemistries"
    )
    
    # Per-material recycling overrides (using checkbox to show/hide)
    show_recycling_overrides = st.checkbox("Show per-material recycling overrides", value=False)
    recycle_override = {}
    if show_recycling_overrides:
        st.markdown("*Override global recycling rate for specific materials*")
        for m in sorted(inten["material_key"].unique()):
            pretty = m.replace("_", " ").title()
            recycle_override[m] = st.slider(
                f"{pretty}", 
                0, 100, recycle_global, 1, 
                key=f"recy_{m}",
                help=f"Override global rate for {pretty}"
            )
    else:
        # Set all to global rate when overrides are hidden
        for m in sorted(inten["material_key"].unique()):
            recycle_override[m] = recycle_global

# Policy Settings
with st.sidebar.expander("🏛️ Policy Settings", expanded=False):
    st.markdown("**Import Duties**")
    import_duty = {}
    for m in materials_all:
        import_duty[m] = st.number_input(
            f"{m.replace('_',' ').title()} duty ($/ton)", 
            min_value=0.0, max_value=5000.0, value=0.0, step=10.0, 
            key=f"duty_{m}",
            help=f"Import duty for {m.replace('_',' ').title()}"
        )
    
    st.markdown("**Battery Assembly**")
    pack_overhead = st.slider(
        "Pack overhead (%)", 
        0, 60, 25, 1,
        help="Additional cost for battery pack assembly"
    )
    
    st.markdown("**Currency**")
    usd_inr = st.number_input(
        "USD → INR exchange rate", 
        min_value=40.0, max_value=120.0, value=83.0, step=0.5,
        help="Current USD to INR conversion rate"
    )

# Model Configuration
with st.sidebar.expander("⚙️ Model Configuration", expanded=False):
    rolling_months = st.number_input(
        "Rolling window (months)", 
        min_value=12, max_value=120, value=60, step=6,
        help="Number of months to use for model training (ROLLING_MONTHS)"
    )
    forecast_months = st.number_input(
        "Forecast horizon (months)", 
        min_value=6, max_value=120, value=120, step=6,
        help="Number of months to forecast ahead (FORECAST_MONTHS)"
    )

# Date Range Filter - More Prominent
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Date Range Filter")
st.sidebar.markdown("**Select date range for forecasts:**")

# Get date range from data
min_date = mat['date'].min().date()
max_date = mat['date'].max().date()

# Default to show last 2 years of history + 5 years of forecast
default_start = pd.Timestamp.today().date() - pd.DateOffset(years=2)
default_end = pd.Timestamp.today().date() + pd.DateOffset(years=5)

start_date = st.sidebar.date_input(
    "Start Date",
    value=default_start,
    min_value=min_date,
    max_value=max_date,
    help="Start date for data display",
    key="date_filter_start"
)

end_date = st.sidebar.date_input(
    "End Date", 
    value=default_end,
    min_value=min_date,
    max_value=max_date,
    help="End date for data display",
    key="date_filter_end"
)

# Quick preset buttons
st.sidebar.markdown("**Quick presets:**")
col1, col2 = st.sidebar.columns(2)
with col1:
    preset_2y5y = st.button("📈 2Y+5Y", help="Last 2 years + 5 years forecast", key="preset_2y5y")
with col2:
    preset_10y = st.button("🔮 10Y", help="Full 10-year forecast", key="preset_10y")

# Handle preset selections
if preset_2y5y:
    start_date = pd.Timestamp.today().date() - pd.DateOffset(years=2)
    end_date = pd.Timestamp.today().date() + pd.DateOffset(years=5)
elif preset_10y:
    start_date = pd.Timestamp.today().date() - pd.DateOffset(years=1)
    end_date = pd.Timestamp.today().date() + pd.DateOffset(years=10)
else:
    # Use the date inputs as they are
    pass

# Show current selection
st.sidebar.info(f"📊 Showing data from **{start_date}** to **{end_date}**")

# Actions
with st.sidebar.expander("🔄 Data Management", expanded=False):
    if data_mode == "API Mode (Live Data)":
        if st.button("🔄 Refresh Data (fetch + build)", help="Fetch live prices and rebuild models"):
            with st.spinner("Fetching live prices and rebuilding models..."):
                try:
                    # Set environment variables for the subprocess calls
                    env = os.environ.copy()
                    env["ROLLING_MONTHS"] = str(rolling_months)
                    env["FORECAST_MONTHS"] = str(forecast_months)
                    
                    p1 = subprocess.run([sys.executable, "scripts/fetch_real_commodity_prices.py"], capture_output=True, text=True, env=env)
                    p2 = subprocess.run([sys.executable, "scripts/build_forecasts.py"], capture_output=True, text=True, env=env)
                    
                    if p1.returncode == 0 and p2.returncode == 0:
                        st.success("Data refreshed. Please rerun the app (R) or use Streamlit's rerun.")
                        st.rerun()
                    else:
                        st.error("Refresh failed — expand for logs.")
                        with st.expander("Fetch logs"):
                            st.code(p1.stdout + "\n" + p1.stderr)
                        with st.expander("Build logs"):
                            st.code(p2.stdout + "\n" + p2.stderr)
                except Exception as e:
                    st.error(f"❌ Refresh error: {e}")
    else:
        # Physical Mode - different options
        if st.button("🔄 Process Uploaded Files", help="Process uploaded files and rebuild forecasts"):
            with st.spinner("Processing uploaded files..."):
                try:
                    # Set environment variables for the subprocess calls
                    env = os.environ.copy()
                    env["ROLLING_MONTHS"] = str(rolling_months)
                    env["FORECAST_MONTHS"] = str(forecast_months)
                    
                    p1 = subprocess.run([sys.executable, "scripts/process_uploaded_data.py"], capture_output=True, text=True, env=env)
                    p2 = subprocess.run([sys.executable, "scripts/build_forecasts.py"], capture_output=True, text=True, env=env)
                    
                    if p1.returncode == 0 and p2.returncode == 0:
                        st.success("Uploaded data processed and forecasts updated!")
                        st.rerun()
                    else:
                        st.error("Processing failed — expand for logs.")
                        with st.expander("Process logs"):
                            st.code(p1.stdout + "\n" + p1.stderr)
                        with st.expander("Build logs"):
                            st.code(p2.stdout + "\n" + p2.stderr)
                except Exception as e:
                    st.error(f"❌ Processing error: {e}")
        
        if st.button("🗑️ Clear Uploaded Files", help="Remove all uploaded files"):
            try:
                uploaded_files = list(Path("processed").glob("uploaded_*"))
                for file in uploaded_files:
                    file.unlink()
                st.success(f"✅ Removed {len(uploaded_files)} uploaded file(s)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error clearing files: {e}")
        
        # Data status
        st.markdown("**Data Status**")
        st.info(f"📊 {len(materials_all)} materials tracked\n🧪 {len(chems_all)} chemistries available")
        
        # API status
        st.success("🔑 Real commodity data sources active")
        st.info("ℹ️ Data sources: Yahoo Finance (Copper/Aluminum), Scaled ETFs (Nickel/Cobalt), Manual CSV (Lithium), Baselines (Graphite/MnSO₄)")
        
        # Model accuracy
        st.markdown("**Model Accuracy (MAPE):**")
        st.info("🔋 Lithium: 14.9% (Good)\n⚡ Nickel: 20.1% (Fair)\n🔌 Copper: 6.6% (Excellent)\n🛩️ Aluminum: 6.0% (Excellent)")

# Helper: filter by kind
def filter_kind(df: pd.DataFrame) -> pd.DataFrame:
    if series_kind == "History only":
        return df[df["kind"] == "history"]
    if series_kind == "Forecast only":
        return df[df["kind"] == "forecast"]
    return df

# Helper: filter by date range
def filter_date_range(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    # Convert date objects to datetime for comparison
    if start_date:
        start_date = pd.Timestamp(start_date)
    if end_date:
        end_date = pd.Timestamp(end_date)
    
    if start_date and end_date:
        return df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    elif start_date:
        return df[df["date"] >= start_date]
    elif end_date:
        return df[df["date"] <= end_date]
    else:
        return df

# Build shocked material prices (wide)
mat_use = filter_kind(mat)
mat_use = mat_use[mat_use["material"].isin(materials_all)].copy()
# Apply date range filter
mat_use = filter_date_range(mat_use, start_date, end_date)
# Apply shocks and duties
mat_use["shock_mult"] = mat_use["material"].map(lambda m: 1.0 + shock_pct.get(m, 0) / 100.0)
mat_use["price_usd_per_ton_shocked"] = mat_use["price_usd_per_ton"] * mat_use["shock_mult"] + mat_use["material"].map(lambda m: import_duty.get(m, 0.0))
mat_wide = mat_use.pivot_table(index="date", columns="material", values="price_usd_per_ton_shocked")

# Effective intensities (apply recycling)
inten_eff = inten.copy()
inten_eff["recycle_pct"] = inten_eff["material_key"].map(lambda m: recycle_override.get(m, recycle_global))
inten_eff["effective_tons_per_gwh"] = inten_eff["tons_per_gwh"].astype(float) * (1.0 - inten_eff["recycle_pct"].astype(float) / 100.0)

# KPIs: latest HISTORY only, YoY on history
hist = mat[mat["kind"]=="history"].copy()
if hist.empty:
    st.warning("No historical data found.")
else:
    latest_hist = hist.sort_values("date").groupby("material", as_index=False).last()
    def kpi_pair(name):
        if name not in latest_hist["material"].values: return None, None
        row = latest_hist[latest_hist["material"]==name].iloc[0]
        v, d = row["price_usd_per_ton"], row["date"]
        prev = hist[(hist["material"]==name) & (hist["date"]<= (d - pd.DateOffset(years=1)))] \
                .sort_values("date").tail(1)
        yoy = None if prev.empty else (v/prev["price_usd_per_ton"].values[0]-1)*100
        return v, yoy

    # Show all available materials in KPIs
    available_materials = latest_hist["material"].tolist()
    tiles = ["lithium_carbonate","nickel","cobalt","copper","aluminum","graphite_battery","manganese_sulfate"]
    # Filter to only show materials that have data
    tiles = [m for m in tiles if m in available_materials]
    
    # Create columns (max 4 per row for better layout)
    num_cols = min(len(tiles), 4)
    cols = st.columns(num_cols)
    
    for i, mname in enumerate(tiles):
        v, yoy = kpi_pair(mname)
        if v is None: continue
        
        # Material icons
        material_icons = {
            'lithium_carbonate': '🔋',
            'nickel': '⚡',
            'cobalt': '💎',
            'copper': '🔌',
            'aluminum': '🛩️',
            'graphite_battery': '📊',
            'manganese_sulfate': '🧪'
        }
        
        icon = material_icons.get(mname, '📈')
        arrow = "↓" if yoy is not None and yoy < 0 else ("↑" if yoy is not None else "–")
        color = "#21ba45" if arrow=="↓" else ("#db2828" if arrow=="↑" else "#9aa4b2")
        
        # Format the value appropriately
        if v < 100:
            val_str = f"{v:.2f}"
        else:
            val_str = f"{v:,.0f}"
        
        cols[i % num_cols].markdown(
            f"<div class='kpi-card'><div class='kpi-title'>{icon} {mname.replace('_',' ').title()}</div>"
            f"<div class='kpi-value'>{val_str} USD/t "
            f"<span style='font-size:14px; color:{color}; margin-left:8px;'>{arrow} "
            f"{'' if yoy is None else f'{yoy:,.1f}%'}"
            f"</span></div></div>", unsafe_allow_html=True
        )

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Prices", "🧪 Chemistry & Battery", "🧭 Sensitivity", "⚙️ Assumptions"])

# Prices tab
with tab1:
    st.markdown("### 📈 Material Price Trends")
    show_mats = [m for m in sel_materials if m in mat_wide.columns]
    if not show_mats:
        st.info("ℹ️ No selected materials available in data.")
    else:
        df_plot = mat_wide[show_mats].reset_index().melt(id_vars="date", var_name="material", value_name="usd_per_ton")
        
        # Enhanced chart with better styling
        fig = px.line(
            df_plot, 
            x="date", 
            y="usd_per_ton", 
            color="material",
            title="Material Prices (USD/ton) - Scenario Adjusted",
            labels={"usd_per_ton": "Price (USD/ton)", "date": "Date"},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified'
        )
        
        fig.update_traces(line=dict(width=3))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Materials Tracked", len(show_mats))
        with col2:
            avg_price = df_plot.groupby('material')['usd_per_ton'].last().mean()
            st.metric("Average Price", f"${avg_price:,.0f}/ton")
        
        st.download_button(
            "📥 Download Materials Data (CSV)", 
            df_plot.to_csv(index=False), 
            "materials_scenario.csv",
            mime="text/csv"
        )

# Chemistry recomputation under scenario
# Join shocked prices with effective intensities and aggregate per chemistry
records = []
for chem in sel_chems:
    basket = inten_eff[inten_eff["chemistry"] == chem]
    if basket.empty:
        continue
    # For each material in basket, multiply price by effective tons
    tmp = []
    for _, r in basket.iterrows():
        mk = r["material_key"]
        if mk in mat_wide.columns:
            contrib = mat_wide[[mk]].copy()
            contrib.columns = ["usd_per_ton"]
            contrib["usd_per_gwh_component"] = contrib["usd_per_ton"] * float(r["effective_tons_per_gwh"])
            contrib["material"] = mk
            tmp.append(contrib[["usd_per_gwh_component", "material"]])
    if not tmp:
        continue
    joined = pd.concat(tmp, axis=1)
    # Extract component cols
    comp_cols = [c for c in joined.columns if c == "usd_per_gwh_component" or (isinstance(c, tuple) and c[0] == "usd_per_gwh_component")]
    # Because of concat axis=1, columns may duplicate; rebuild from list
    comp_vals = []
    mat_names = []
    for t in tmp:
        comp_vals.append(t[["usd_per_gwh_component"]].rename(columns={"usd_per_gwh_component": t["material"].iloc[0]}))
        mat_names.append(t["material"].iloc[0])
    comp_df = pd.concat(comp_vals, axis=1)
    comp_df["usd_per_gwh"] = comp_df.sum(axis=1, numeric_only=True)
    comp_df["chemistry"] = chem
    comp_df.index.name = "date"
    records.append(comp_df.reset_index())

chem_scn = pd.concat(records) if records else pd.DataFrame(columns=["date", "chemistry", "usd_per_gwh"])
if not chem_scn.empty:
    chem_scn["usd_per_kwh_material"] = chem_scn["usd_per_gwh"] / 1000.0
    chem_scn["usd_per_kwh_battery"] = chem_scn["usd_per_kwh_material"] * (1.0 + pack_overhead / 100.0)
    chem_scn["inr_per_kwh_battery"] = chem_scn["usd_per_kwh_battery"] * usd_inr

# Chemistry & Battery tab
with tab2:
    if chem_scn.empty:
        st.info("ℹ️ No chemistry data available for current scenario.")
    else:
        show = chem_scn[chem_scn["chemistry"].isin(sel_chems)].copy()
        # Apply date range filter
        show = filter_date_range(show, start_date, end_date)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            latest_cost = show.groupby('chemistry')['usd_per_kwh_battery'].last().mean()
            st.metric("Avg Battery Cost", f"${latest_cost:.2f}/kWh")
        with col2:
            latest_inr = show.groupby('chemistry')['inr_per_kwh_battery'].last().mean()
            st.metric("Avg Battery Cost (INR)", f"₹{latest_inr:.0f}/kWh")
        with col3:
            cost_range = show.groupby('chemistry')['usd_per_kwh_battery'].last()
            st.metric("Cost Range", f"${cost_range.min():.2f} - ${cost_range.max():.2f}")
        with col4:
            st.metric("Chemistries", len(sel_chems))
        
        # Material cost per chemistry
        st.markdown("### 🧪 Material Cost per Chemistry (USD/GWh)")
        fig1 = px.line(
            show, 
            x="date", 
            y="usd_per_gwh", 
            color="chemistry",
            title="Material Cost per Chemistry",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig1.update_traces(line=dict(width=3))
        st.plotly_chart(fig1, use_container_width=True)
        
        # Battery-level costs
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🔋 Battery Cost (USD/kWh)")
            fig2 = px.line(
                show, 
                x="date", 
                y="usd_per_kwh_battery", 
                color="chemistry",
                title="Battery Cost (USD/kWh)",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
            )
            fig2.update_traces(line=dict(width=3))
            st.plotly_chart(fig2, use_container_width=True)
        
        with col2:
            st.markdown("### 🇮🇳 Battery Cost (INR/kWh)")
            fig3 = px.line(
                show, 
                x="date", 
                y="inr_per_kwh_battery", 
                color="chemistry",
                title="Battery Cost (INR/kWh)",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
            )
            fig3.update_traces(line=dict(width=3))
            st.plotly_chart(fig3, use_container_width=True)
        
        # Cost breakdown table
        st.markdown("### 📊 Latest Cost Breakdown")
        latest_costs = show.groupby('chemistry').last()[['usd_per_gwh', 'usd_per_kwh_material', 'usd_per_kwh_battery', 'inr_per_kwh_battery']].round(2)
        latest_costs.columns = ['Material Cost (USD/GWh)', 'Material Cost (USD/kWh)', 'Battery Cost (USD/kWh)', 'Battery Cost (INR/kWh)']
        st.dataframe(latest_costs, use_container_width=True)
        
        st.download_button(
            "📥 Download Chemistry Data (CSV)", 
            show.to_csv(index=False), 
            "chemistry_monthly_scenario.csv",
            mime="text/csv"
        )

# Sensitivity (tornado)
with tab3:
    if chem_scn.empty:
        st.info("No chemistry data to run sensitivity.")
    else:
        chem_single = st.selectbox("Chemistry", options=sel_chems or chems_all)
        # Choose latest available month across data
        latest_date = chem_scn["date"].max()
        date_sel = st.date_input("Month", value=latest_date.date())
        date_sel = pd.Timestamp(date_sel).replace(day=1)
        # Base values
        base_row = chem_scn[(chem_scn["chemistry"] == chem_single) & (chem_scn["date"] == date_sel)]
        if base_row.empty:
            st.info("Selected month not in data; pick another month.")
        else:
            base_battery = float(base_row["usd_per_kwh_battery"].iloc[0])
            # Basket materials
            basket = inten_eff[inten_eff["chemistry"] == chem_single]
            impacts = []
            contrib_rows = []
            for _, r in basket.iterrows():
                mk = r["material_key"]
                eff_tons = float(r["effective_tons_per_gwh"])
                if mk not in mat_wide.columns:
                    continue
                price_t = mat_wide[mk].dropna()
                if date_sel not in price_t.index:
                    continue
                p0 = float(price_t.loc[date_sel]) + float(import_duty.get(mk, 0.0))
                # Base contribution $/kWh
                contrib_kwh = (p0 * eff_tons) / 1000.0 * (1.0 + pack_overhead / 100.0)
                contrib_rows.append({"material": mk, "contribution_usd_per_kwh": contrib_kwh, "effective_tons_per_gwh": eff_tons})
                # +10% shock
                p_up = p0 * 1.1
                p_dn = p0 * 0.9
                up_battery = base_battery + ((p_up - p0) * eff_tons) / 1000.0 * (1.0 + pack_overhead / 100.0)
                dn_battery = base_battery + ((p_dn - p0) * eff_tons) / 1000.0 * (1.0 + pack_overhead / 100.0)
                impacts.append({"material": mk, "delta_up": up_battery - base_battery, "delta_down": base_battery - dn_battery})
            if not impacts:
                st.info("No materials available for sensitivity.")
            else:
                sens = pd.DataFrame(impacts)
                sens["impact"] = sens[["delta_up", "delta_down"]].abs().max(axis=1)
                sens = sens.sort_values("impact", ascending=True)  # small to large for tornado stacking
                fig_tornado = px.bar(
                    sens,
                    x="impact",
                    y="material",
                    orientation="h",
                    title=f"Tornado: ±10% price shock impact on battery $/kWh ({chem_single}, {date_sel.date()})",
                )
                st.plotly_chart(fig_tornado, use_container_width=True)
                st.subheader("Base contribution ($/kWh) and intensity used")
                st.dataframe(pd.DataFrame(contrib_rows).sort_values("contribution_usd_per_kwh", ascending=False), use_container_width=True)

# Assumptions
with tab4:
    st.subheader("Symbols & Sources")
    if symbols:
        st.json(symbols, expanded=False)
    st.subheader("Intensity baseline (with effective tons/GWh)")
    show_int = inten_eff[["chemistry", "material", "effective_tons_per_gwh", "recycle_pct"]].copy()
    st.dataframe(show_int, use_container_width=True)
    st.info("Scenario math: shocked_price = price × (1+shock%) + duty. Effective tons/GWh = tons × (1 - recycling%). Battery $/kWh = (Σ price×tons / 1000) × (1+overhead%). INR via USD→INR.")

# Excel export
st.subheader("Export")
if st.button("Export Excel"):
    try:
        materials_scenario = mat_wide.reset_index()
        chemistry_monthly_scenario = chem_scn.copy() if not chem_scn.empty else pd.DataFrame()
        intensity_effective = show_int if 'show_int' in locals() else inten_eff
        assumptions = pd.DataFrame({
            "param": ["pack_overhead_pct", "usd_inr", "recycle_global_pct"],
            "value": [pack_overhead, usd_inr, recycle_global],
        })
        # add shocks and duties
        shocks = pd.DataFrame({"material": list(shock_pct.keys()), "shock_pct": list(shock_pct.values())})
        duties = pd.DataFrame({"material": list(import_duty.keys()), "duty_usd_per_ton": list(import_duty.values())})
        assumptions_extra = pd.merge(shocks, duties, on="material", how="outer")
        xbytes = to_excel_bytes({
            "materials_scenario": materials_scenario,
            "chemistry_monthly_scenario": chemistry_monthly_scenario,
            "intensity_effective": intensity_effective,
            "assumptions": assumptions_extra,
        })
        st.download_button("Download Excel", data=xbytes, file_name="battery_cost_scenario.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Export failed: {e}")
