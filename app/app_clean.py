"""
Battery Cost Forecast Streamlit Application - Clean Version.

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
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .kpi-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .kpi-title {
        font-size: 14px;
        font-weight: 600;
        color: #4a5568;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: #2d3748;
    }
    </style>
    """, unsafe_allow_html=True
)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🔋 Battery Cost Forecaster</h1>
    <p>Advanced scenario modeling and cost analysis for battery materials</p>
</div>
""", unsafe_allow_html=True)

# Check if data exists
def load_data():
    """Load data and return status."""
    try:
        # Check if processed files exist
        if Path("processed/material_forecasts.csv").exists() and Path("processed/chemistry_costs_monthly.csv").exists():
            mat = pd.read_csv("processed/material_forecasts.csv", parse_dates=["date"])
            chem_mo = pd.read_csv("processed/chemistry_costs_monthly.csv", parse_dates=["date"])
            data_loaded = True
        else:
            mat = None
            chem_mo = None
            data_loaded = False
            
        # Load intensity data (should always exist)
        inten = pd.read_csv("data/intensity_baseline.csv")
        
        # Load symbols metadata if available
        symbols = {}
        if Path("processed/symbols_te.json").exists():
            symbols = json.loads(Path("processed/symbols_te.json").read_text())
            
        return data_loaded, mat, chem_mo, inten, symbols
        
    except Exception as e:
        st.error(f"❌ **Error loading data:** {str(e)}")
        st.stop()

# Load data
data_loaded, mat, chem_mo, inten, symbols = load_data()

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

# Main app content (only shown if data is loaded)
if data_loaded and mat is not None and chem_mo is not None:
    # Normalize intensity names to price columns
    inten["material_norm"] = inten["material"].str.lower().str.replace(" ", "_", regex=False)
    inten_alias = {"manganese": "manganese_sulfate"}
    inten["material_key"] = inten["material_norm"].map(lambda x: inten_alias.get(x, x))

    # Materials list
    materials_all = sorted(mat["material"].unique())
    chems_all = sorted(inten["chemistry"].unique())

    # Sidebar
    st.sidebar.markdown("## ⚙️ Control Panel")
    
    # Data Source Mode
    st.sidebar.markdown("### 🔧 Data Source Mode")
    data_mode = st.sidebar.radio(
        "Choose data source:",
        ["API Mode (Live Data)", "Physical Mode (Upload Files)"],
        help="API Mode fetches live prices, Physical Mode uses uploaded files",
        key="data_source_mode"
    )

    # Series Selection
    with st.sidebar.expander("📊 Data Series", expanded=True):
        sel_materials = st.multiselect(
            "Materials to analyze", 
            options=materials_all, 
            default=materials_all,
            help="Select materials to display in charts"
        )
        
        sel_chems = st.multiselect(
            "Chemistries to analyze",
            options=chems_all,
            default=chems_all,
            help="Select battery chemistries to analyze"
        )
        
        series_kind = st.selectbox(
            "Data type",
            ["All", "History only", "Forecast only"],
            help="Filter by data type"
        )

    # Date Range Filter - ONLY if data is loaded
    st.sidebar.markdown("### 📅 Date Range Filter")
    
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

    # Data Management
    with st.sidebar.expander("🔄 Data Management", expanded=False):
        if data_mode == "API Mode (Live Data)":
            if st.button("🔄 Refresh Data", help="Fetch live prices and rebuild models"):
                with st.spinner("Fetching live data..."):
                    try:
                        result1 = subprocess.run([sys.executable, "scripts/fetch_real_commodity_prices.py"], 
                                               capture_output=True, text=True)
                        result2 = subprocess.run([sys.executable, "scripts/build_forecasts.py"], 
                                               capture_output=True, text=True)
                        
                        if result1.returncode == 0 and result2.returncode == 0:
                            st.success("✅ Data refreshed!")
                            st.rerun()
                        else:
                            st.error("❌ Refresh failed")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # Helper functions
    def filter_kind(df: pd.DataFrame) -> pd.DataFrame:
        if series_kind == "History only":
            return df[df["kind"] == "history"]
        if series_kind == "Forecast only":
            return df[df["kind"] == "forecast"]
        return df

    def filter_date_range(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
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

    # Main content
    st.markdown("## 📊 Battery Material Cost Analysis")
    
    # KPIs
    st.markdown("### 📈 Key Performance Indicators")
    
    # Get latest historical data for KPIs
    hist_data = mat[mat["kind"] == "history"].copy()
    hist_data = filter_date_range(hist_data, start_date, end_date)
    
    # Calculate YoY changes
    def calculate_yoy(series, material_name):
        if len(series) < 12:
            return None
        try:
            latest = series.iloc[-1]
            year_ago = series.iloc[-12] if len(series) >= 12 else series.iloc[0]
            return ((latest - year_ago) / year_ago) * 100
        except:
            return None
    
    # Display KPIs
    materials_to_show = ["lithium_carbonate", "nickel", "copper", "aluminum"]
    cols = st.columns(len(materials_to_show))
    
    for i, mname in enumerate(materials_to_show):
        if mname in hist_data["material"].values:
            material_data = hist_data[hist_data["material"] == mname].sort_values("date")
            if not material_data.empty:
                latest_price = material_data["price_usd_per_ton"].iloc[-1]
                yoy = calculate_yoy(material_data["price_usd_per_ton"], mname)
                
                icon = {"lithium_carbonate": "🔋", "nickel": "⚡", "copper": "🔌", "aluminum": "🛩️"}.get(mname, "📈")
                arrow = "↓" if yoy is not None and yoy < 0 else ("↑" if yoy is not None else "–")
                color = "#21ba45" if arrow=="↓" else ("#db2828" if arrow=="↑" else "#9aa4b2")
                
                cols[i].markdown(
                    f"<div class='kpi-card'><div class='kpi-title'>{icon} {mname.replace('_',' ').title()}</div>"
                    f"<div class='kpi-value'>${latest_price:,.0f}/ton "
                    f"<span style='font-size:14px; color:{color}; margin-left:8px;'>{arrow} "
                    f"{'' if yoy is None else f'{yoy:,.1f}%'}"
                    f"</span></div></div>", unsafe_allow_html=True
                )

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Prices", "🧪 Chemistry Costs", "⚙️ Assumptions"])

    # Prices tab
    with tab1:
        st.markdown("### 📈 Material Price Trends")
        
        # Filter data
        mat_use = filter_kind(mat)
        mat_use = mat_use[mat_use["material"].isin(sel_materials)].copy()
        mat_use = filter_date_range(mat_use, start_date, end_date)
        
        if not mat_use.empty:
            # Create chart
            fig = px.line(
                mat_use, 
                x="date", 
                y="price_usd_per_ton", 
                color="material",
                title="Material Prices Over Time",
                labels={"price_usd_per_ton": "Price (USD/ton)", "date": "Date"}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Materials Tracked", len(sel_materials))
            with col2:
                avg_price = mat_use.groupby('material')['price_usd_per_ton'].last().mean()
                st.metric("Average Price", f"${avg_price:,.0f}/ton")
        else:
            st.info("No data available for selected materials and date range.")

    # Chemistry Costs tab
    with tab2:
        st.markdown("### 🧪 Battery Chemistry Costs")
        
        # Filter chemistry data
        chem_use = filter_kind(chem_mo)
        chem_use = chem_use[chem_use["chemistry"].isin(sel_chems)].copy()
        chem_use = filter_date_range(chem_use, start_date, end_date)
        
        if not chem_use.empty:
            # Create chart
            fig = px.line(
                chem_use,
                x="date",
                y="usd_per_gwh",
                color="chemistry",
                title="Battery Chemistry Costs Over Time",
                labels={"usd_per_gwh": "Cost (USD/GWh)", "date": "Date"}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Chemistries Tracked", len(sel_chems))
            with col2:
                avg_cost = chem_use.groupby('chemistry')['usd_per_gwh'].last().mean()
                st.metric("Average Cost", f"${avg_cost:,.0f}/GWh")
        else:
            st.info("No chemistry cost data available for selected date range.")

    # Assumptions tab
    with tab3:
        st.markdown("### ⚙️ Model Assumptions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Data Sources")
            if symbols:
                for material, info in symbols.items():
                    st.markdown(f"**{material.replace('_', ' ').title()}:**")
                    st.markdown(f"- Source: {info.get('source', 'Unknown')}")
                    if 'symbol' in info:
                        st.markdown(f"- Symbol: {info['symbol']}")
                    if 'note' in info:
                        st.markdown(f"- Note: {info['note']}")
                    st.markdown("")
            else:
                st.info("No data source information available.")
        
        with col2:
            st.markdown("#### 🧪 Material Intensities")
            st.dataframe(inten[["chemistry", "material", "tons_per_gwh"]], use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("**🔋 Battery Cost Forecast App** - Built with Streamlit")

else:
    st.error("❌ **Data loading failed.** Please check your data files and try again.")
