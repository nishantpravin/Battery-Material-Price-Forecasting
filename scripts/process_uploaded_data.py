"""
Process uploaded CSV/Excel files and integrate them into the forecasting pipeline.

This script reads uploaded files from the processed/ folder and creates
a unified price panel for forecasting.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Directories
PROCESSED_DIR = Path("processed")
DATA_DIR = Path("data")

def process_uploaded_files():
    """Process all uploaded files and create a unified price panel."""
    print("🔄 Processing uploaded files...")
    
    # Find all uploaded files
    uploaded_files = list(PROCESSED_DIR.glob("uploaded_*"))
    
    if not uploaded_files:
        print("❌ No uploaded files found in processed/ folder")
        return False
    
    print(f"📁 Found {len(uploaded_files)} uploaded file(s)")
    
    # Target materials
    target_materials = [
        "lithium_carbonate", "nickel", "cobalt", "manganese_sulfate", 
        "graphite_battery", "copper", "aluminum"
    ]
    
    # Initialize price panel
    months = pd.date_range("2020-01-01", pd.Timestamp.today().normalize().replace(day=1), freq="MS")
    price_panel = pd.DataFrame({"date": months})
    
    # Process each uploaded file
    for file_path in uploaded_files:
        try:
            print(f"📄 Processing {file_path.name}...")
            
            # Read file
            if file_path.suffix == '.csv':
                df = pd.read_csv(file_path)
            else:  # Excel
                df = pd.read_excel(file_path)
            
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)}")
            
            # Try to identify date and price columns
            date_col = None
            price_col = None
            material_col = None
            
            # Look for date column
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['date', 'time', 'month', 'year']):
                    date_col = col
                    break
            
            # Look for price column
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['price', 'cost', 'usd', 'ton', 'per_ton']):
                    price_col = col
                    break
            
            # Look for material column
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['material', 'commodity', 'metal', 'name']):
                    material_col = col
                    break
            
            print(f"   Detected columns - Date: {date_col}, Price: {price_col}, Material: {material_col}")
            
            if date_col and price_col:
                # Convert date column
                df[date_col] = pd.to_datetime(df[date_col])
                
                if material_col:
                    # Multiple materials in one file
                    for material in df[material_col].unique():
                        material_data = df[df[material_col] == material].copy()
                        
                        # Normalize material name
                        material_name = normalize_material_name(material)
                        
                        if material_name in target_materials:
                            # Resample to monthly
                            monthly_data = material_data.set_index(date_col)[price_col].resample('MS').mean()
                            
                            # Merge with price panel
                            temp_df = pd.DataFrame({
                                'date': monthly_data.index,
                                material_name: monthly_data.values
                            })
                            price_panel = price_panel.merge(temp_df, on='date', how='left', suffixes=('', '_new'))
                            
                            # Use new data if available
                            if f'{material_name}_new' in price_panel.columns:
                                price_panel[material_name] = price_panel[f'{material_name}_new'].fillna(price_panel[material_name])
                                price_panel = price_panel.drop(columns=[f'{material_name}_new'])
                            
                            print(f"   ✅ Added {material_name}: {len(monthly_data)} months")
                else:
                    # Single material file - try to guess from filename
                    material_name = guess_material_from_filename(file_path.name)
                    
                    if material_name in target_materials:
                        # Resample to monthly
                        monthly_data = df.set_index(date_col)[price_col].resample('MS').mean()
                        
                        # Merge with price panel
                        temp_df = pd.DataFrame({
                            'date': monthly_data.index,
                            material_name: monthly_data.values
                        })
                        price_panel = price_panel.merge(temp_df, on='date', how='left', suffixes=('', '_new'))
                        
                        # Use new data if available
                        if f'{material_name}_new' in price_panel.columns:
                            price_panel[material_name] = price_panel[f'{material_name}_new'].fillna(price_panel[material_name])
                            price_panel = price_panel.drop(columns=[f'{material_name}_new'])
                        
                        print(f"   ✅ Added {material_name}: {len(monthly_data)} months")
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")
            continue
    
    # Ensure all target columns exist
    for material in target_materials:
        if material not in price_panel.columns:
            price_panel[material] = np.nan
    
    # Reorder columns
    price_panel = price_panel[["date"] + target_materials].sort_values("date")
    
    # Save the processed price panel
    output_path = PROCESSED_DIR / "prices_monthly.csv"
    price_panel.to_csv(output_path, index=False)
    
    print(f"✅ Saved unified price panel to {output_path}")
    print(f"📊 Data shape: {price_panel.shape}")
    
    # Show summary
    print("\n📈 Data Summary:")
    for material in target_materials:
        non_null_count = price_panel[material].notna().sum()
        if non_null_count > 0:
            latest_price = price_panel[material].dropna().iloc[-1]
            print(f"   {material}: {non_null_count} months, latest: ${latest_price:,.2f}/ton")
        else:
            print(f"   {material}: No data")
    
    return True

def normalize_material_name(name):
    """Normalize material names to match target materials."""
    name = str(name).lower().strip()
    
    # Mapping
    mapping = {
        'lithium': 'lithium_carbonate',
        'lithium carbonate': 'lithium_carbonate',
        'li2co3': 'lithium_carbonate',
        'nickel': 'nickel',
        'ni': 'nickel',
        'cobalt': 'cobalt',
        'co': 'cobalt',
        'manganese': 'manganese_sulfate',
        'manganese sulfate': 'manganese_sulfate',
        'mnso4': 'manganese_sulfate',
        'graphite': 'graphite_battery',
        'graphite battery': 'graphite_battery',
        'copper': 'copper',
        'cu': 'copper',
        'aluminum': 'aluminum',
        'aluminium': 'aluminum',
        'al': 'aluminum'
    }
    
    return mapping.get(name, name)

def guess_material_from_filename(filename):
    """Guess material name from filename."""
    filename = filename.lower()
    
    if 'lithium' in filename:
        return 'lithium_carbonate'
    elif 'nickel' in filename:
        return 'nickel'
    elif 'cobalt' in filename:
        return 'cobalt'
    elif 'manganese' in filename:
        return 'manganese_sulfate'
    elif 'graphite' in filename:
        return 'graphite_battery'
    elif 'copper' in filename:
        return 'copper'
    elif 'aluminum' in filename or 'aluminium' in filename:
        return 'aluminum'
    else:
        return None

def main():
    """Main function."""
    print("🔋 Processing Uploaded Material Price Files")
    print("=" * 50)
    
    success = process_uploaded_files()
    
    if success:
        print("\n✅ Uploaded data processing completed!")
        print("🔄 Now run: python scripts/build_forecasts.py")
    else:
        print("\n❌ Uploaded data processing failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
