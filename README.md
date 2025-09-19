# 🔋 Battery Cost Forecast App

A production-ready Python application for forecasting battery material costs with **10-year forecasting**, real commodity prices, and interactive scenario modeling.

## ✨ Features

- **📈 10-Year Forecasting**: ETS models with configurable horizons (6-120 months)
- **💰 Real Commodity Prices**: Live data from Yahoo Finance with proper scaling
- **🎯 Model Accuracy**: Transparent MAPE metrics for all materials
- **📅 Date Filtering**: Interactive date range selection for custom analysis
- **🔄 Scenario Modeling**: Price shocks, recycling rates, import duties
- **📊 Sensitivity Analysis**: Tornado charts showing material impact
- **💾 Excel Export**: Multi-sheet workbooks with all data
- **🌐 Modern UI**: Dark-friendly, responsive design with material icons

## 🚀 Quick Start

### 1. Setup Environment
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
# or source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 2. Run the App
```bash
streamlit run app/app.py
```

**That's it!** The app will automatically fetch live commodity prices and generate forecasts.

## 📊 Model Accuracy (MAPE)

| Material | Accuracy | Rating |
|----------|----------|---------|
| 🔌 Copper | 6.6% | Excellent |
| 🛩️ Aluminum | 6.0% | Excellent |
| 🔋 Lithium | 14.9% | Good |
| ⚡ Nickel | 20.1% | Fair |

## 🎯 Data Sources

- **Yahoo Finance**: Live futures data (Copper, Aluminum)
- **Scaled ETFs**: Realistic pricing (Nickel, Cobalt, Lithium)
- **Manual CSV**: Current market data (Lithium Carbonate)
- **Industry Baselines**: Standard pricing (Graphite, Manganese Sulfate)

## 🔧 Configuration

### Environment Variables
```bash
# Optional: Override forecast parameters
$env:FORECAST_MONTHS = "120"  # 10 years
$env:ROLLING_MONTHS = "60"    # 5 years training window

# Optional: Override data sources
$env:GRAPHITE_CSV_URL = "https://your-data.csv"
$env:MNSULFATE_CSV_URL = "https://your-data.csv"
```

### App Controls
- **Date Range Filter**: Select custom time periods
- **Forecast Horizon**: 6-120 months (default: 120)
- **Rolling Window**: 12-120 months (default: 60)
- **Scenario Modeling**: Price shocks, recycling, duties

## 📁 Project Structure

```
battery-cost-forecast/
├── app/
│   └── app.py                 # Streamlit dashboard
├── scripts/
│   ├── fetch_real_commodity_prices.py  # Live data fetcher
│   └── build_forecasts.py     # ETS forecasting
├── data/
│   ├── intensity_baseline.csv # Material intensities
│   └── lithium_manual.csv     # Manual lithium data
├── src/
│   ├── units.py              # Unit conversions
│   ├── symbol_resolver.py    # Symbol resolution
│   └── utils_io.py           # Excel export
├── processed/                # Generated data (gitignored)
├── requirements.txt
└── README.md
```

## 📈 Usage Examples

### Basic Forecasting
1. Open the app
2. Select materials in sidebar
3. Choose "History + Forecast" 
4. View 10-year price projections

### Scenario Analysis
1. Go to "🧪 Chemistry & Battery" tab
2. Adjust price shock sliders
3. Set recycling rates
4. View impact on battery costs

### Sensitivity Analysis
1. Go to "🧭 Sensitivity" tab
2. Select chemistry and month
3. View tornado chart
4. See material contribution impact

## 🔬 Technical Details

### Forecasting Model
- **Method**: Exponential Smoothing (ETS) with additive trend
- **Training**: Rolling window (configurable, default 60 months)
- **Horizon**: Configurable (default 120 months = 10 years)
- **Validation**: Walk-forward with MAPE metrics

### Data Pipeline
1. **Fetch**: Live commodity prices from multiple sources
2. **Process**: Unit conversion, monthly resampling
3. **Forecast**: ETS model fitting and prediction
4. **Visualize**: Interactive charts and analysis

### Performance
- **Data Refresh**: ~30 seconds for full pipeline
- **Forecast Generation**: ~5 seconds for all materials
- **UI Responsiveness**: Real-time scenario updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Data Sources**: Check `processed/symbols_te.json` for source details

---

**Built with ❤️ for the battery industry** 🔋⚡
