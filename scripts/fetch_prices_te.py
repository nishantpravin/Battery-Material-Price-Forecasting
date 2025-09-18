"""
Fetch battery material prices from TradingEconomics with fallbacks.

This script fetches historical price data for battery materials from TradingEconomics,
with fallbacks to Yahoo Finance and baseline values for missing data.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import tradingeconomics as te
except ImportError:
    print("Warning: tradingeconomics package not found. Install with: pip install tradingeconomics")
    te = None

try:
    import yfinance as yf
except ImportError:
    print("Warning: yfinance package not found. Install with: pip install yfinance")
    yf = None

from units import to_usd_per_ton, detect_unit_from_string, get_conversion_info
from symbol_resolver import resolve_symbols_te


def get_apikey() -> Optional[str]:
    """Get TradingEconomics API key from environment or Streamlit secrets."""
    # Try environment variable first
    apikey = os.getenv('apikey')
    if apikey:
        return apikey
    
    # Try Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'apikey' in st.secrets:
            return st.secrets['apikey']
    except:
        pass
    
    return None


def login_te(primary: Optional[str] = None) -> bool:
    """
    Login to TradingEconomics with primary key or guest credentials.
    
    Args:
        primary: Primary API key to try first
        
    Returns:
        True if login successful, False otherwise
    """
    if not te:
        print("TradingEconomics SDK not available")
        return False
    
    # Try primary key first
    if primary:
        try:
            te.login(primary)
            print(f"Logged in with primary key: {primary[:10]}...")
            return True
        except Exception as e:
            print(f"Primary key login failed: {e}")
    
    # Try guest credentials
    try:
        te.login('guest:guest')
        print("Logged in with guest credentials")
        return True
    except Exception as e:
        print(f"Guest login failed: {e}")
        return False


def get_commodities_df(primary_apikey: Optional[str] = None) -> Tuple[pd.DataFrame, bool]:
    """
    Get TradingEconomics commodities dataframe.
    
    Returns:
        Tuple of (dataframe, used_guest_for_discovery)
    """
    if not te:
        return pd.DataFrame(), False
    
    used_guest = False
    try:
        # Try with primary key first, if provided
        if primary_apikey:
            try:
                te.login(primary_apikey)
                df = te.getMarketsData(marketsField='commodities', output_type='df')
                if df is not None and not df.empty:
                    df.columns = [col.lower() for col in df.columns]
                    print(f"Retrieved {len(df)} commodities from TradingEconomics (primary)")
                    return df, False
                else:
                    print("No commodities data returned on primary key; trying guest for discovery...")
            except Exception as e:
                print(f"Primary commodities discovery failed: {e}")

        # Guest discovery
        te.login('guest:guest')
        df = te.getMarketsData(marketsField='commodities', output_type='df')
        if df is not None and not df.empty:
            df.columns = [col.lower() for col in df.columns]
            print(f"Retrieved {len(df)} commodities from TradingEconomics (guest discovery)")
            used_guest = True
            return df, used_guest
        else:
            print("No commodities data returned from guest discovery")
            return pd.DataFrame(), used_guest
    except Exception as e:
        print(f"Error getting commodities data: {e}")
        return pd.DataFrame(), used_guest


def fetch_historical_data_te(symbol: str, init_date: str = '2016-01-01') -> pd.DataFrame:
    """
    Fetch historical data for a symbol from TradingEconomics.
    
    Args:
        symbol: TradingEconomics symbol
        init_date: Start date for historical data
        
    Returns:
        DataFrame with historical data
    """
    if not te:
        return pd.DataFrame()
    
    try:
        # Try getHistoricalData first
        df = te.getHistoricalData(symbol=symbol, initDate=init_date, output_type='df')
        
        if df is not None and not df.empty:
            return df
        
        # Try getMarketsHistorical as fallback
        df = te.getMarketsHistorical(symbols=[symbol], initDate=init_date, output_type='df')
        
        if df is not None and not df.empty:
            return df
            
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
    
    return pd.DataFrame()


def fetch_historical_with_user_then_guest(symbol: str, init_date: str, primary_apikey: Optional[str]) -> Tuple[pd.DataFrame, str]:
    """Try fetching TE history with the user's key first; if empty, try guest.

    Returns (df, note) where note indicates which credential worked: 'primary'|'guest'|'none'.
    """
    if not te:
        return pd.DataFrame(), 'none'

    # Try primary first if provided
    if primary_apikey:
        try:
            te.login(primary_apikey)
            df = fetch_historical_data_te(symbol, init_date)
            if df is not None and not df.empty:
                return df, 'primary'
        except Exception as e:
            print(f"Primary fetch failed for {symbol}: {e}")

    # Try guest
    try:
        te.login('guest:guest')
        df = fetch_historical_data_te(symbol, init_date)
        if df is not None and not df.empty:
            return df, 'guest'
    except Exception as e:
        print(f"Guest fetch failed for {symbol}: {e}")

    return pd.DataFrame(), 'none'


def fetch_yahoo_data(symbol: str, start_date: str = '2016-01-01') -> pd.DataFrame:
    """
    Fetch data from Yahoo Finance as fallback.
    
    Args:
        symbol: Yahoo Finance symbol
        start_date: Start date for data
        
    Returns:
        DataFrame with historical data
    """
    if not yf:
        return pd.DataFrame()
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date)
        
        if not df.empty:
            # Reset index to get Date as column
            df = df.reset_index()
            # Rename columns to match expected format
            df = df.rename(columns={'Date': 'date', 'Close': 'close'})
            return df[['date', 'close']]
            
    except Exception as e:
        print(f"Error fetching Yahoo data for {symbol}: {e}")
    
    return pd.DataFrame()


def resample_to_monthly(df: pd.DataFrame, price_col: str = 'close') -> pd.DataFrame:
    """
    Resample daily data to monthly averages.
    
    Args:
        df: DataFrame with daily data
        price_col: Name of price column
        
    Returns:
        DataFrame with monthly data
    """
    if df.empty:
        return df
    
    # Ensure date column is datetime (timezone-naive)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        # If timezone-aware, convert to UTC then remove tz info
        if hasattr(df['date'].dt, 'tz') and df['date'].dt.tz is not None:
            df['date'] = df['date'].dt.tz_convert('UTC').dt.tz_localize(None)
        df = df.set_index('date')
    elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_convert('UTC').tz_localize(None)
    
    # Resample to monthly start (MS) and take mean
    monthly = df.resample('MS')[price_col].mean().reset_index()
    monthly.columns = ['date', price_col]
    
    return monthly


def get_baseline_prices() -> Dict[str, float]:
    """Get baseline prices for materials that can't be fetched."""
    return {
        'graphite_battery': 7000.0,  # USD/ton
        'manganese_sulfate': 1100.0,  # USD/ton
        'lithium_carbonate': 15000.0,  # USD/ton (fallback)
        'cobalt': 35000.0,  # USD/ton (fallback)
        'nickel': 20000.0,  # USD/ton (fallback)
        # Proxies to support LFP composition
        'phosphate_rock': 120.0,   # USD/ton (proxy baseline)
        'iron_ore': 100.0,         # USD/ton (proxy baseline)
    }


def main():
    """Main function to fetch and process all price data."""
    print("Starting battery material price fetching...")
    
    # Get API key
    apikey = get_apikey()
    if not apikey:
        print("Warning: No TradingEconomics API key found. Using guest credentials and fallbacks.")
    
    # Login to TradingEconomics
    login_success = login_te(apikey)
    if not login_success:
        print("Failed to login to TradingEconomics. Proceeding with fallbacks only.")
    
    # Get commodities data (try primary then guest discovery)
    commodities_df, used_guest_discovery = get_commodities_df(apikey)
    
    # Resolve symbols for target materials
    target_materials = ['nickel', 'cobalt', 'copper', 'aluminum', 'lithium_carbonate', 'manganese_sulfate', 'graphite_battery', 'phosphate_rock', 'iron_ore']
    resolved_symbols = {}
    
    if not commodities_df.empty:
        resolved_symbols = resolve_symbols_te(commodities_df)
    else:
        print("No commodities data available. Using fallback symbols.")
        # Define fallback symbols
        resolved_symbols = {
            'copper': {'symbol': 'HG=F', 'name': 'Copper Futures', 'unit': 'USD/LB'},
            'aluminum': {'symbol': 'ALI=F', 'name': 'Aluminum Futures', 'unit': 'USD/TON'},
            'nickel': {'symbol': 'NID=F', 'name': 'Nickel Futures', 'unit': 'USD/TON'},
        }
    
    # Initialize results
    all_prices = {}
    symbols_metadata = {}
    
    # Fetch data for each material
    for material in target_materials:
        print(f"\nProcessing {material}...")
        
        if material in resolved_symbols:
            symbol_info = resolved_symbols[material]
            symbol = symbol_info['symbol']
            unit = symbol_info['unit']
            
            # Try TradingEconomics first (user then guest)
            df, which_cred = fetch_historical_with_user_then_guest(symbol, '2016-01-01', apikey)
            
            if not df.empty:
                # Convert to USD/ton
                price_col = 'close' if 'close' in df.columns else 'last'
                if price_col in df.columns:
                    converted_prices = []
                    for price in df[price_col]:
                        converted = to_usd_per_ton(price, unit)
                        converted_prices.append(converted if converted is not None else price)
                    
                    df['price_usd_per_ton'] = converted_prices
                    monthly_df = resample_to_monthly(df, 'price_usd_per_ton')
                    
                    if not monthly_df.empty:
                        all_prices[material] = monthly_df
                        symbols_metadata[material] = {
                            'source': 'TE',
                            'symbol': symbol,
                            'unit': unit,
                            'notes': ('guest fetch used' if which_cred == 'guest' else 'primary key')
                        }
                        print(f"  ✓ Fetched {len(monthly_df)} monthly prices from TE")
                        continue
            
        # Even if no TE symbol was resolved, try Yahoo for certain materials
            if material in ['copper', 'aluminum', 'nickel']:
                yahoo_symbols = {
                    'copper': 'HG=F',
                    'aluminum': 'ALI=F', 
                    'nickel': 'NID=F'
                }
                
                ysym = yahoo_symbols[material]
                yahoo_df = fetch_yahoo_data(ysym)
                # Try alternative nickel symbol if first fails
                if material == 'nickel' and (yahoo_df is None or yahoo_df.empty):
                    alt = 'NI=F'
                    print("  Yahoo fallback alt symbol for nickel: NI=F")
                    yahoo_df = fetch_yahoo_data(alt)
                    if yahoo_df is not None and not yahoo_df.empty:
                        ysym = alt
                if not yahoo_df.empty:
                    # Convert units
                    if material == 'copper':  # USD/lb to USD/ton
                        yahoo_df['price_usd_per_ton'] = yahoo_df['close'] * 2204.62262185
                    else:  # Already in USD/ton
                        yahoo_df['price_usd_per_ton'] = yahoo_df['close']
                    
                    monthly_df = resample_to_monthly(yahoo_df, 'price_usd_per_ton')
                    if not monthly_df.empty:
                        all_prices[material] = monthly_df
                        symbols_metadata[material] = {
                            'source': 'Yahoo',
                            'symbol': ysym,
                            'unit': 'USD/LB' if material == 'copper' else 'USD/TON',
                            'notes': 'Yahoo Finance fallback'
                        }
                        print(f"  ✓ Fetched {len(monthly_df)} monthly prices from Yahoo")
                        continue
        
        # Use baseline if no data available
        baseline_prices = get_baseline_prices()
        if material in baseline_prices:
            # Create a baseline series with current date
            baseline_df = pd.DataFrame({
                'date': [datetime.now().replace(day=1)],
                'price_usd_per_ton': [baseline_prices[material]]
            })
            all_prices[material] = baseline_df
            symbols_metadata[material] = {
                'source': 'Baseline',
                'symbol': '',
                'unit': 'USD/TON',
                'notes': 'baseline used'
            }
            print(f"  ⚠ Using baseline price: ${baseline_prices[material]:,.0f}/ton")
        else:
            print(f"  ✗ No data available for {material}")
    
    # Combine all prices into a single DataFrame
    if all_prices:
        # Find the common date range
        all_dates = set()
        for df in all_prices.values():
            all_dates.update(df['date'].dt.date)
        
        # Create date range
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            date_range = pd.date_range(start=min_date, end=max_date, freq='MS')
            
            # Create combined DataFrame
            combined_df = pd.DataFrame({'date': date_range})
            
            # Add each material's prices
            for material, df in all_prices.items():
                df_copy = df.copy()
                df_copy['date'] = pd.to_datetime(df_copy['date'])
                combined_df = combined_df.merge(
                    df_copy[['date', 'price_usd_per_ton']], 
                    on='date', 
                    how='left'
                )
                combined_df = combined_df.rename(columns={'price_usd_per_ton': material})
            
            # Save combined prices
            os.makedirs('processed', exist_ok=True)
            combined_df.to_csv('processed/prices_monthly.csv', index=False)
            print(f"\n✓ Saved combined prices to processed/prices_monthly.csv")
            print(f"  Date range: {min_date} to {max_date}")
            print(f"  Materials: {list(all_prices.keys())}")
        
        # Save metadata
        with open('processed/symbols_te.json', 'w') as f:
            json.dump(symbols_metadata, f, indent=2, default=str)
        print(f"✓ Saved metadata to processed/symbols_te.json")
        
    else:
        print("No price data was successfully fetched!")


if __name__ == "__main__":
    main()
