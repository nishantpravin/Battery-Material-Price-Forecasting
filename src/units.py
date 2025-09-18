"""
Unit conversion utilities for battery material prices.

This module provides functions to normalize various price units to USD/ton
for consistent analysis across different data sources.
"""

import re
from typing import Optional

# Conversion constants
LB_TO_TON = 2204.62262185
KG_TO_TON = 1000
OZ_TO_TON = 32000  # Approximate for precious metals


def to_usd_per_ton(value: float, unit: Optional[str], usd_per_cny: Optional[float] = 0.14) -> Optional[float]:
    """
    Convert a price value to USD/ton based on the given unit.
    
    Args:
        value: The price value to convert
        unit: The unit string (e.g., "USD/lb", "CNY/T", "USD/oz")
        usd_per_cny: USD to CNY exchange rate (default 0.14 ≈ 1/7.0)
        
    Returns:
        Converted price in USD/ton, or None if unit is not recognized
        
    Examples:
        >>> to_usd_per_ton(100, "USD/lb")
        220462.262185
        >>> to_usd_per_ton(1000, "USD/kg")
        1000000.0
        >>> to_usd_per_ton(50000, "CNY/T", 0.14)
        7000.0
    """
    if value is None or unit is None:
        return None
        
    # Normalize unit string
    unit_clean = str(unit).strip().upper()
    
    # Direct USD/ton units (no conversion needed)
    if re.match(r'USD/(MT|T|TON|TONNE|METRICTON)$', unit_clean):
        return value
    
    # USD/lb conversion
    if unit_clean == 'USD/LB':
        return value * LB_TO_TON
    
    # USD/kg conversion  
    if unit_clean == 'USD/KG':
        return value * KG_TO_TON
    
    # USD/oz conversion (for precious metals)
    if unit_clean == 'USD/OZ':
        return value * OZ_TO_TON
    
    # Cents/lb conversion (divide by 100 first, then convert)
    if unit_clean in ['CENTS/LB', 'USC/LB']:
        return (value / 100) * LB_TO_TON
    
    # CNY units (convert to USD first)
    if re.match(r'CNY/(MT|T|TON|TONNE)$', unit_clean):
        return value * usd_per_cny
    
    # If no match found, return None
    return None


def detect_unit_from_string(unit_str: str) -> str:
    """
    Detect and normalize unit string from various formats.
    
    Args:
        unit_str: Raw unit string from data source
        
    Returns:
        Normalized unit string
    """
    if not unit_str:
        return ""
        
    unit_clean = str(unit_str).strip().upper()
    
    # Map common variations to standard forms
    unit_mappings = {
        'USD/MT': 'USD/TON',
        'USD/T': 'USD/TON', 
        'USD/TONNE': 'USD/TON',
        'USD/METRICTON': 'USD/TON',
        'CNY/MT': 'CNY/TON',
        'CNY/T': 'CNY/TON',
        'CNY/TONNE': 'CNY/TON',
        'CENTS/LB': 'CENTS/LB',
        'USC/LB': 'CENTS/LB'
    }
    
    return unit_mappings.get(unit_clean, unit_clean)


def get_conversion_info(unit: str) -> dict:
    """
    Get information about unit conversion for logging purposes.
    
    Args:
        unit: The unit string
        
    Returns:
        Dictionary with conversion information
    """
    unit_clean = detect_unit_from_string(unit)
    
    if re.match(r'USD/(MT|T|TON|TONNE|METRICTON)$', unit_clean):
        return {
            'conversion': 'none',
            'factor': 1.0,
            'description': 'Already in USD/ton'
        }
    elif unit_clean == 'USD/LB':
        return {
            'conversion': 'lb_to_ton',
            'factor': LB_TO_TON,
            'description': f'Converted from USD/lb using factor {LB_TO_TON}'
        }
    elif unit_clean == 'USD/KG':
        return {
            'conversion': 'kg_to_ton', 
            'factor': KG_TO_TON,
            'description': f'Converted from USD/kg using factor {KG_TO_TON}'
        }
    elif unit_clean == 'USD/OZ':
        return {
            'conversion': 'oz_to_ton',
            'factor': OZ_TO_TON,
            'description': f'Converted from USD/oz using factor {OZ_TO_TON}'
        }
    elif unit_clean in ['CENTS/LB', 'USC/LB']:
        return {
            'conversion': 'cents_lb_to_ton',
            'factor': LB_TO_TON / 100,
            'description': f'Converted from cents/lb using factor {LB_TO_TON/100}'
        }
    elif re.match(r'CNY/(MT|T|TON|TONNE)$', unit_clean):
        return {
            'conversion': 'cny_to_usd',
            'factor': 'usd_per_cny',
            'description': 'Converted from CNY using USD/CNY exchange rate'
        }
    else:
        return {
            'conversion': 'unknown',
            'factor': None,
            'description': f'Unknown unit: {unit_clean}'
        }


# Test cases (can be run with: python -m doctest src/units.py)
if __name__ == "__main__":
    # Test basic conversions
    assert to_usd_per_ton(100, "USD/lb") == 220462.262185
    assert to_usd_per_ton(1000, "USD/kg") == 1000000.0
    assert to_usd_per_ton(50000, "CNY/T", 0.14) == 7000.0
    assert to_usd_per_ton(100, "USD/TON") == 100.0
    assert to_usd_per_ton(50, "CENTS/LB") == 1102.311310925
    
    print("All unit conversion tests passed!")

