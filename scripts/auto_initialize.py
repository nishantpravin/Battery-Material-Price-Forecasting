"""
Auto-initialize data if processed files don't exist.

This script checks if the required processed files exist,
and if not, automatically initializes them.
"""

import os
import sys
from pathlib import Path

def check_and_initialize():
    """Check if data exists, initialize if not."""
    processed_dir = Path("processed")
    required_files = [
        "processed/prices_monthly.csv",
        "processed/material_forecasts.csv", 
        "processed/chemistry_costs_monthly.csv"
    ]
    
    # Check if all required files exist
    all_exist = all(Path(f).exists() for f in required_files)
    
    if not all_exist:
        print("🔋 Auto-initializing data...")
        try:
            # Run initialization
            result = os.system(f"{sys.executable} scripts/initialize_data.py")
            return result == 0
        except Exception as e:
            print(f"❌ Auto-initialization failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = check_and_initialize()
    sys.exit(0 if success else 1)
