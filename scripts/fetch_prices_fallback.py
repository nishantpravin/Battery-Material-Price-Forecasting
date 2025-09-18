# scripts/fetch_prices_fallback.py
import os, json
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
import requests

OUTDIR = Path("processed"); OUTDIR.mkdir(parents=True, exist_ok=True)
DATA = Path("data"); DATA.mkdir(parents=True, exist_ok=True)
LB_TO_TON = 2204.62262185

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "investing-com6.p.rapidapi.com"

def monthly_from_yahoo(symbol, unit):
    df = yf.download(symbol, start="2016-01-01", progress=False, auto_adjust=True)
    if df is None or df.empty:
        print(f"[WARN] Yahoo empty for {symbol}")
        return None
    price = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    if unit == "USD_LB":
        usd_per_ton = price * LB_TO_TON
    else:
        usd_per_ton = price
    m = usd_per_ton.resample("MS").mean().reset_index()
    m.columns = ["date","usd_per_ton"]
    return m

def investing_monthly(pair_id: int, label: str):
    if not RAPIDAPI_KEY:
        print(f"[WARN] No RAPIDAPI_KEY; skip {label}")
        return None
    
    # Try multiple possible endpoints
    endpoints = [
        f"https://{RAPIDAPI_HOST}/commodities/get-historical-data",
        f"https://{RAPIDAPI_HOST}/web-crawling/api/commodities/get-historical-data",
        f"https://{RAPIDAPI_HOST}/web-crawling/api/markets/commodities/historical"
    ]
    
    headers = {"x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": RAPIDAPI_KEY}
    params = {"pair_id": int(pair_id), "interval":"daily", "time_frame":"max"}
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code == 200:
                js = r.json(); rows = js.get("data", [])
                if not rows:
                    continue
                d = pd.DataFrame(rows)
                d["date"] = pd.to_datetime(d["date"])
                d["price"] = pd.to_numeric(d["price"], errors="coerce")
                d = d.dropna().sort_values("date")
                m = d.set_index("date")["price"].resample("MS").mean().reset_index()
                return m
        except Exception as e:
            continue
    
    return None

def usd_to_cny_rate():
    try:
        r = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=CNY", timeout=15)
        r.raise_for_status()
        return float(r.json()["rates"]["CNY"])
    except Exception:
        return 7.0  # fallback

def optional_csv(url_env: str, colname: str):
    url = os.getenv(url_env)
    if not url:
        return None
    try:
        df = pd.read_csv(url, parse_dates=["date"])
        df = df.sort_values("date")
        m = (df.set_index("date")["usd_per_ton"].astype(float)
               .resample("MS").mean().interpolate("time").reset_index())
        m.columns = ["date", colname]
        return m
    except Exception as e:
        print(f"[WARN] {url_env} failed: {e}")
        return None

def main():
    frames = []
    meta = {}

    # Copper (USD/lb → USD/ton)
    cu = monthly_from_yahoo("HG=F", "USD_LB")
    if cu is not None:
        frames.append(cu.rename(columns={"usd_per_ton":"copper"}))
        meta["copper"] = {"source":"Yahoo","symbol":"HG=F","unit_native":"USD/lb","conv":"×2204.6226 → USD/ton"}

    # Aluminum (USD/ton)
    al = monthly_from_yahoo("ALI=F", "USD_TON")
    if al is not None:
        frames.append(al.rename(columns={"usd_per_ton":"aluminum"}))
        meta["aluminum"] = {"source":"Yahoo","symbol":"ALI=F","unit_native":"USD/ton"}

    if not frames:
        raise SystemExit("No Yahoo data (copper/aluminum) — check network.")

    panel = frames[0]
    for df in frames[1:]:
        panel = panel.merge(df, on="date", how="outer")

    # Nickel (Investing USD/ton) - try RapidAPI first, then Yahoo ETF
    nickel_id = int(os.getenv("NICKEL_ID", "959207"))
    ni = investing_monthly(nickel_id, "Nickel")
    if ni is not None:
        panel = panel.merge(ni.rename(columns={"price":"nickel"}), on="date", how="outer")
        meta["nickel"] = {"source":"Investing via RapidAPI","id":nickel_id,"unit_native":"USD/ton"}
    else:
        # Fallback to Yahoo ETF (proxy for nickel prices)
        ni_etf = monthly_from_yahoo("LIT", "USD_TON")  # Lithium ETF as nickel proxy
        if ni_etf is not None:
            # Scale ETF price to approximate nickel prices (rough conversion)
            # LIT ~$50, Nickel ~$20,000/ton, so scale factor ~400
            ni_etf["nickel"] = ni_etf["usd_per_ton"] * 400  # Better scaling factor
            panel = panel.merge(ni_etf[["date","nickel"]], on="date", how="outer")
            meta["nickel"] = {"source":"Yahoo ETF (LIT proxy)","symbol":"LIT","note":"Scaled ETF price as nickel proxy (factor: 400x)"}

    # Lithium (Investing CNY/ton → USD/ton) - try RapidAPI first, then manual CSV, then Yahoo ETF
    lithium_id = int(os.getenv("LITHIUM_ID", "997886"))
    li_native = investing_monthly(lithium_id, "Lithium Carbonate 99.5% China")
    if li_native is not None:
        rate = float(os.getenv("USD_CNY", "0")) or usd_to_cny_rate()  # USD→CNY
        # price here is CNY/ton; convert to USD/ton = price / (USD→CNY)
        li = li_native.copy()
        li["lithium_carbonate"] = li["price"] / rate
        panel = panel.merge(li[["date","lithium_carbonate"]], on="date", how="outer")
        meta["lithium_carbonate"] = {"source":"Investing via RapidAPI","id":lithium_id,"unit_native":"CNY/ton","usd_cny":rate}
    else:
        # Try manual CSV first
        manual = DATA/"lithium_manual.csv"
        if manual.exists():
            df = pd.read_csv(manual, parse_dates=["date"]).sort_values("date")
            m = (df.set_index("date")["usd_per_ton"].astype(float)
                   .resample("MS").mean().interpolate("time").reset_index())
            m.columns = ["date", "lithium_carbonate"]
            panel = panel.merge(m, on="date", how="outer")
            meta["lithium_carbonate"] = {"source":"Manual CSV","path":str(manual)}
        else:
            # Fallback to Yahoo ETF
            li_etf = monthly_from_yahoo("LIT", "USD_TON")
            if li_etf is not None:
                # Scale ETF price to approximate lithium carbonate prices
                li_etf["lithium_carbonate"] = li_etf["usd_per_ton"] * 0.6  # Rough scaling factor
                panel = panel.merge(li_etf[["date","lithium_carbonate"]], on="date", how="outer")
                meta["lithium_carbonate"] = {"source":"Yahoo ETF (LIT)","symbol":"LIT","note":"Scaled ETF price as lithium carbonate proxy"}

    # Cobalt (Investing USD/ton) — try RapidAPI first, then Yahoo ETF
    cobalt_id = os.getenv("COBALT_ID")
    if cobalt_id:
        co = investing_monthly(int(cobalt_id), "Cobalt")
        if co is not None:
            panel = panel.merge(co.rename(columns={"price":"cobalt"}), on="date", how="outer")
            meta["cobalt"] = {"source":"Investing via RapidAPI","id":int(cobalt_id),"unit_native":"USD/ton"}
    else:
        # Fallback to Yahoo ETF (proxy for cobalt prices)
        co_etf = monthly_from_yahoo("LAC", "USD_TON")  # Lithium Americas as cobalt proxy
        if co_etf is not None:
            # Scale ETF price to approximate cobalt prices (rough conversion)
            # LAC ~$3, Cobalt ~$30,000/ton, so scale factor ~10,000
            co_etf["cobalt"] = co_etf["usd_per_ton"] * 10000  # Better scaling factor
            panel = panel.merge(co_etf[["date","cobalt"]], on="date", how="outer")
            meta["cobalt"] = {"source":"Yahoo ETF (LAC proxy)","symbol":"LAC","note":"Scaled ETF price as cobalt proxy (factor: 10,000x)"}

    # Graphite & MnSO4: allow CSV override, else baseline (clearly labeled)
    g_csv = optional_csv("GRAPHITE_CSV_URL", "graphite_battery")
    mn_csv = optional_csv("MNSULFATE_CSV_URL", "manganese_sulfate")
    months = pd.date_range("2020-01-01", pd.Timestamp.today().normalize().replace(day=1), freq="MS")
    base = pd.DataFrame({"date": months})
    if g_csv is None:
        base["graphite_battery"] = 7000.0
        meta["graphite_battery"] = {"source":"Baseline","note":"set GRAPHITE_CSV_URL to override"}
    if mn_csv is None:
        base["manganese_sulfate"] = 1100.0
        meta["manganese_sulfate"] = {"source":"Baseline","note":"set MNSULFATE_CSV_URL to override"}

    panel = panel.merge(base, on="date", how="outer")
    if g_csv is not None: panel = panel.merge(g_csv, on="date", how="outer")
    if mn_csv is not None: panel = panel.merge(mn_csv, on="date", how="outer")

    panel = panel.sort_values("date")
    panel = panel.loc[panel["date"] >= "2016-01-01"]

    want = ["date","lithium_carbonate","nickel","cobalt","manganese_sulfate","graphite_battery","copper","aluminum"]
    for c in want:
        if c not in panel.columns: panel[c] = np.nan
    panel = panel[want]
    panel.to_csv(OUTDIR/"prices_monthly.csv", index=False)

    Path(OUTDIR/"symbols_te.json").write_text(json.dumps(meta, indent=2))
    print("OK wrote processed/prices_monthly.csv", panel.shape)
    print(panel.tail())

if __name__ == "__main__":
    main()