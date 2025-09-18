# scripts/build_forecasts.py
import os
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.tsa.holtwinters import ExponentialSmoothing

IN_PRICE = Path("processed/prices_monthly.csv")
IN_INTEN = Path("data/intensity_baseline.csv")
OUT_MAT  = Path("processed/material_forecasts.csv")
OUT_CM   = Path("processed/chemistry_costs_monthly.csv")
OUT_CA   = Path("processed/chemistry_costs_annual.csv")

ROLLING_MONTHS = int(os.getenv("ROLLING_MONTHS", "60"))
FORECAST_MONTHS = int(os.getenv("FORECAST_MONTHS", "36"))

TODAY = pd.Timestamp.today().tz_localize(None)
CURRENT_MS = pd.Timestamp(TODAY.year, TODAY.month, 1)

def fit_ets(y: pd.Series):
    y = y.asfreq("MS").interpolate("time").bfill().ffill()
    if y.dropna().shape[0] < 6:
        class Flat:
            def forecast(self, steps): return np.repeat(y.iloc[-1], steps)
        return Flat()
    try:
        return ExponentialSmoothing(y, trend="add", seasonal=None, initialization_method="estimated").fit(optimized=True)
    except Exception:
        class Drift:
            def forecast(self, steps):
                s = y.dropna()
                if len(s) < 2: return np.repeat(s.iloc[-1], steps)
                slope = (s.iloc[-1]-s.iloc[0])/(len(s)-1)
                return np.array([s.iloc[-1]+slope*(i+1) for i in range(steps)])
        return Drift()

def main():
    price_m = pd.read_csv(IN_PRICE, parse_dates=["date"]).set_index("date").sort_index()
    mats = list(price_m.columns)

    rows=[]
    for m in mats:
        s = price_m[m].astype(float).asfreq("MS")
        s = s[s.index <= CURRENT_MS]  # trim to current month
        if s.dropna().empty: continue
        # rolling window
        if len(s.dropna()) > ROLLING_MONTHS:
            s = s.iloc[-ROLLING_MONTHS:]
        model = fit_ets(s)
        start_future = min(s.index.max() + pd.offsets.MonthBegin(1), CURRENT_MS + pd.offsets.MonthBegin(1))
        end_future   = CURRENT_MS + pd.offsets.MonthBegin(FORECAST_MONTHS)
        fidx = pd.date_range(start_future, end_future, freq="MS")
        fc  = pd.DataFrame({"date": fidx, "material": m, "price_usd_per_ton": np.asarray(model.forecast(len(fidx))), "kind":"forecast"})
        hist = pd.DataFrame({"date": s.index, "material": m, "price_usd_per_ton": s.values, "kind":"history"})
        rows.append(pd.concat([hist, fc], ignore_index=True))

    mat_all = pd.concat(rows).sort_values(["material","date"])
    OUT_MAT.parent.mkdir(parents=True, exist_ok=True)
    mat_all.to_csv(OUT_MAT, index=False)

    inten = pd.read_csv(IN_INTEN)
    inten["material_norm"] = inten["material"].str.lower().str.replace(" ","_", regex=False)
    alias = {"manganese":"manganese_sulfate"}
    names = set(mat_all["material"].unique())

    comp=[]
    for chem, grp in inten.groupby("chemistry"):
        for _, r in grp.iterrows():
            key = alias.get(r["material_norm"], r["material_norm"])
            if key not in names: continue
            sub = mat_all[mat_all["material"]==key][["date","price_usd_per_ton","kind"]].copy()
            sub["chemistry"]=chem
            sub["usd_per_gwh_component"] = sub["price_usd_per_ton"] * float(r["tons_per_gwh"])
            comp.append(sub)

    chem_mo = (pd.concat(comp)
                 .groupby(["chemistry","date","kind"], as_index=False)["usd_per_gwh_component"].sum()
                 .rename(columns={"usd_per_gwh_component":"usd_per_gwh"}))
    chem_mo.to_csv(OUT_CM, index=False)

    chem_yr = chem_mo.copy()
    chem_yr["year"] = chem_yr["date"].dt.year
    chem_yr = chem_yr.groupby(["chemistry","year","kind"], as_index=False)["usd_per_gwh"].mean()
    chem_yr.to_csv(OUT_CA, index=False)
    print("OK wrote:", OUT_MAT, OUT_CM, OUT_CA)

if __name__ == "__main__":
    main()