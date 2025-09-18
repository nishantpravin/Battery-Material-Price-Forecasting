# Battery Cost Forecast

A production-ready Python application for forecasting battery material costs and chemistry economics using TradingEconomics data with robust fallbacks.

## Features

- 🔋 **Material Price Tracking**: Fetch true monthly prices for battery materials from TradingEconomics
- 📊 **Unit Normalization**: Transparent conversion to USD/ton with comprehensive unit handling
- 🔮 **ETS Forecasting**: 36-month price forecasts using Exponential Smoothing
- ⚡ **Chemistry Analysis**: Compute $/GWh costs for NMC811, NMC622, NMC532, LFP, and LCO chemistries
- 📈 **Interactive Dashboard**: Streamlit app with charts, sliders, and CSV downloads
- 🛡️ **Robust Fallbacks**: Guest discovery, Yahoo Finance, and baseline values for missing data

## Target Materials

- Lithium Carbonate
- Nickel
- Cobalt
- Manganese Sulfate
- Graphite Battery
- Copper
- Aluminum

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Set your TradingEconomics API key as an environment variable:

**Windows (PowerShell):**
```powershell
$env:apikey="YOUR_KEY[:SECRET]"
```

**Mac/Linux:**
```bash
export apikey="YOUR_KEY[:SECRET]"
```

**Streamlit Cloud:**
Create `.streamlit/secrets.toml`:
```toml
apikey = "YOUR_KEY[:SECRET]"
```

### 3. Run the Application

```bash
# Fetch price data
python scripts/fetch_prices_te.py

# Build forecasts and compute chemistry costs
python scripts/build_forecasts.py

# Launch Streamlit app
streamlit run app/app.py
```

## Project Structure

```
battery-cost-forecast/
├── app/
│   └── app.py                    # Streamlit dashboard
├── data/
│   └── intensity_baseline.csv    # Material intensities per chemistry
├── processed/                    # Generated files (gitignored)
│   ├── prices_monthly.csv        # Normalized monthly prices
│   ├── material_forecasts.csv    # ETS forecasts
│   ├── chemistry_costs_monthly.csv
│   ├── chemistry_costs_annual.csv
│   └── symbols_te.json          # Data source metadata
├── scripts/
│   ├── fetch_prices_te.py       # Data fetching with fallbacks
│   └── build_forecasts.py       # Forecasting and cost computation
├── src/
│   ├── units.py                 # Unit conversion utilities
│   └── symbol_resolver.py       # TE symbol resolution
├── .gitignore
├── requirements.txt
└── README.md
```

## Data Sources & Fallbacks

### Primary: TradingEconomics
- Uses official `tradingeconomics` Python package
- Automatic symbol resolution by material name patterns
- Guest discovery if user key lacks commodities access

### Fallbacks
- **Yahoo Finance**: Copper (HG=F), Aluminum (ALI=F), Nickel (NID=F)
- **Baseline Values**: Graphite ($7,000/ton), Manganese Sulfate ($1,100/ton)

### Unit Conversions
All prices normalized to USD/ton:
- USD/lb → × 2,204.62
- USD/kg → × 1,000
- USD/oz → × 32,000
- CNY/ton → × USD/CNY rate (default 0.14)

## Forecasting Methodology

- **ETS Model**: Exponential Smoothing with additive trend, no seasonality
- **Horizon**: 36 months forward
- **Fallback**: Simple linear trend extrapolation if ETS fails
- **Interpolation**: Forward/backward fill for missing monthly values

## Chemistry Cost Calculation

Cost per GWh = Σ(price_usd_per_ton × tons_per_gwh) across all materials

Material intensities defined in `data/intensity_baseline.csv`:
- NMC811: High-nickel cathode (22 tons Ni/GWh)
- NMC622: Balanced nickel-cobalt (16.5 tons Ni/GWh)
- NMC532: Lower nickel content (12.5 tons Ni/GWh)
- LFP: Iron phosphate (14 tons P, 12 tons Fe/GWh)
- LCO: Lithium cobalt oxide (28 tons Co/GWh)

## Streamlit Dashboard

### Tabs
1. **Prices**: Interactive charts for material prices with forecast toggle
2. **Chemistry $/GWh**: Cost analysis with download buttons
3. **Assumptions**: Data sources, unit conversions, and baseline values

### Features
- Multi-select materials and chemistries
- Toggle historical vs forecast data
- CSV download for monthly/annual costs
- Data source transparency

## Error Handling

- Never crashes on single series failure
- Clear logging of symbol selection, unit detection, and conversions
- Graceful degradation with baseline values
- Helpful error messages in Streamlit app

## API Key Requirements

If your TradingEconomics key lacks commodities access:
1. The app will use guest credentials for symbol discovery
2. Attempts to fetch with your key first, falls back to guest
3. Contact TradingEconomics to enable markets access for full functionality

## Dependencies

- `pandas>=2.2` - Data manipulation
- `numpy>=1.26` - Numerical computing
- `statsmodels>=0.14` - ETS forecasting
- `tradingeconomics>=4.5.0` - Primary data source
- `yfinance>=0.2.60` - Fallback data source
- `streamlit>=1.37` - Web dashboard
- `plotly>=5.23` - Interactive charts

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues or questions:
1. Check the error messages in the Streamlit app
2. Verify your API key has commodities access
3. Ensure all required files are generated by running the scripts in order
4. Check the `processed/symbols_te.json` file for data source information

