"""
TradingEconomics symbol resolution for battery materials.

This module provides functions to resolve the best TradingEconomics symbols
for battery materials based on name patterns and scoring criteria.
"""

import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def resolve_symbols_te(te_dataframe: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """
    Resolve TradingEconomics symbols for target battery materials.
    
    Args:
        te_dataframe: TE commodities dataframe with lowercase columns
        
    Returns:
        Dictionary mapping material names to symbol info:
        {
            "nickel": {"symbol": "...", "name": "...", "unit": "..."},
            "cobalt": {"symbol": "...", "name": "...", "unit": "..."},
            ...
        }
    """
    # Target materials and their regex patterns
    target_materials = {
        "nickel": r"\bnickel\b",
        "cobalt": r"\bcobalt\b", 
        "copper": r"\bcopper\b",
        "aluminum": r"\baluminum\b|\baluminium\b",
        "lithium_carbonate": r"\blithium\b",
        "manganese_sulfate": r"\bmanganese\b",
        "graphite_battery": r"\bgraphite\b"
    }
    
    resolved_symbols = {}
    
    for material, pattern in target_materials.items():
        candidates = find_symbol_candidates(te_dataframe, pattern)
        if candidates:
            best_symbol = select_best_symbol(candidates)
            resolved_symbols[material] = best_symbol
            print(f"Resolved {material}: {best_symbol['symbol']} ({best_symbol['name']}) - {best_symbol['unit']}")
        else:
            print(f"No symbol found for {material}")
    
    return resolved_symbols


def find_symbol_candidates(df: pd.DataFrame, pattern: str) -> List[Dict[str, str]]:
    """
    Find all symbol candidates matching the given pattern.
    
    Args:
        df: TE commodities dataframe
        pattern: Regex pattern to match against symbol names
        
    Returns:
        List of candidate dictionaries with symbol info
    """
    candidates = []
    
    if df.empty:
        return candidates
    
    # Ensure we have the expected columns (lowercase)
    required_cols = ['symbol', 'name', 'unit']
    if not all(col in df.columns for col in required_cols):
        print(f"Warning: Missing required columns. Available: {list(df.columns)}")
        return candidates
    
    # Search through all rows
    for _, row in df.iterrows():
        name = str(row.get('name', '')).lower()
        symbol = str(row.get('symbol', ''))
        unit = str(row.get('unit', ''))
        
        # Check if name matches pattern
        if re.search(pattern, name, re.IGNORECASE):
            candidates.append({
                'symbol': symbol,
                'name': row.get('name', ''),
                'unit': unit,
                'lastupdate': row.get('lastupdate', ''),
                'score': calculate_symbol_score(unit, row.get('lastupdate', ''))
            })
    
    return candidates


def calculate_symbol_score(unit: str, lastupdate: str) -> float:
    """
    Calculate a score for symbol selection based on unit preference and recency.
    
    Args:
        unit: The unit string
        lastupdate: Last update timestamp
        
    Returns:
        Score (higher is better)
    """
    score = 0.0
    
    # Unit scoring (prefer ton-based units)
    unit_upper = str(unit).upper()
    if any(ton_unit in unit_upper for ton_unit in ['TON', 'MT', 'T']):
        score += 10.0
    elif 'LB' in unit_upper:
        score += 5.0
    elif 'KG' in unit_upper:
        score += 3.0
    elif 'OZ' in unit_upper:
        score += 1.0
    
    # Currency preference (USD preferred)
    if 'USD' in unit_upper:
        score += 5.0
    elif 'CNY' in unit_upper:
        score += 2.0
    
    # Recency scoring (if we have a date)
    if lastupdate:
        try:
            # Try to parse the date (format may vary)
            if isinstance(lastupdate, str):
                # Common TE date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
                    try:
                        update_date = datetime.strptime(lastupdate.split()[0], fmt)
                        days_old = (datetime.now() - update_date).days
                        # Score decreases with age (max 5 points for very recent)
                        recency_score = max(0, 5 - (days_old / 30))  # 5 points for < 1 month
                        score += recency_score
                        break
                    except ValueError:
                        continue
        except Exception:
            # If date parsing fails, give a neutral score
            score += 2.5
    
    return score


def select_best_symbol(candidates: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Select the best symbol from candidates based on scoring.
    
    Args:
        candidates: List of candidate symbol dictionaries
        
    Returns:
        Best symbol dictionary
    """
    if not candidates:
        return {}
    
    # Sort by score (descending) and return the best
    best = max(candidates, key=lambda x: x.get('score', 0))
    
    # Return only the essential fields
    return {
        'symbol': best['symbol'],
        'name': best['name'],
        'unit': best['unit']
    }


def get_material_mapping() -> Dict[str, str]:
    """
    Get mapping from intensity file material names to price column names.
    
    Returns:
        Dictionary mapping intensity material names to price column names
    """
    return {
        'Nickel': 'nickel',
        'Cobalt': 'cobalt', 
        'Manganese': 'manganese_sulfate',
        'Lithium Carbonate': 'lithium_carbonate',
        'Graphite': 'graphite_battery',
        'Copper': 'copper',
        'Aluminum': 'aluminum',
        'Phosphate Rock': 'phosphate_rock',  # For LFP
        'Iron Ore': 'iron_ore'  # For LFP
    }


def normalize_material_name(name: str) -> str:
    """
    Normalize material name from intensity file to price column format.
    
    Args:
        name: Material name from intensity file
        
    Returns:
        Normalized name matching price column format
    """
    mapping = get_material_mapping()
    return mapping.get(name, name.lower().replace(' ', '_'))


# Test function
if __name__ == "__main__":
    # Create a sample dataframe for testing
    test_data = pd.DataFrame({
        'symbol': ['NICKEL1', 'COBALT1', 'COPPER1', 'LITHIUM1'],
        'name': ['Nickel Futures', 'Cobalt Spot', 'Copper Futures', 'Lithium Carbonate'],
        'unit': ['USD/TON', 'USD/LB', 'USD/TON', 'USD/KG'],
        'lastupdate': ['2024-01-15', '2024-01-10', '2024-01-20', '2024-01-12']
    })
    
    result = resolve_symbols_te(test_data)
    print("Test results:")
    for material, info in result.items():
        print(f"  {material}: {info}")

