"""
Initialize data for the Battery Cost Forecast app.

This script runs the data fetching and forecasting pipeline
to create the initial processed data files.
"""

import os
import sys
from pathlib import Path

def main():
    """Initialize data by running the data pipeline."""
    print("🔋 Initializing Battery Cost Forecast Data")
    print("=" * 50)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Create processed directory if it doesn't exist
    processed_dir = Path("processed")
    processed_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Fetch real commodity prices
        print("\n🌐 Step 1: Fetching real commodity prices...")
        result1 = os.system(f"{sys.executable} scripts/fetch_real_commodity_prices.py")
        
        if result1 != 0:
            print("❌ Failed to fetch commodity prices")
            return 1
        
        # Step 2: Build forecasts
        print("\n📊 Step 2: Building forecasts...")
        result2 = os.system(f"{sys.executable} scripts/build_forecasts.py")
        
        if result2 != 0:
            print("❌ Failed to build forecasts")
            return 1
        
        # Verify files were created
        required_files = [
            "processed/prices_monthly.csv",
            "processed/material_forecasts.csv", 
            "processed/chemistry_costs_monthly.csv",
            "processed/chemistry_costs_annual.csv",
            "processed/symbols_te.json"
        ]
        
        print("\n✅ Verifying created files...")
        for file_path in required_files:
            if Path(file_path).exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} - MISSING")
                return 1
        
        print("\n🎉 Data initialization completed successfully!")
        print("🚀 Your app is now ready to use!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
