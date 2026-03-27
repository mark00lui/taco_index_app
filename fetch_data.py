"""
TACO Stress Index — Data Fetcher
自動從免費公開數據源抓取四大壓力指標，零 API Key。

Data Sources:
  T (Treasury Spread) — US Treasury.gov (公開 CSV)
  A (Anxiety / VIX)   — Yahoo Finance (公開端點)
  C (Credit Spread)    — Yahoo Finance HYG ETF + Treasury yield 計算
  O (Outflow Pressure) — Yahoo Finance 市場數據合成指標

All sources are free and require NO API key.
"""

import json
import datetime
import sys
import os
from urllib.request import urlopen, Request
from urllib.error import URLError
import csv
import io

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_url(url, timeout=15):
    """Fetch URL with proper headers."""
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ──────────────────────────────────────────────
# T: Treasury 10Y-2Y Spread from Treasury.gov
# ──────────────────────────────────────────────
def fetch_treasury_spread():
    """
    Fetch 10Y and 2Y yields from US Treasury.gov public CSV.
    Returns spread in percentage (e.g., 0.46 means +0.46%).
    """
    year = datetime.date.today().year
    url = (
        f"https://home.treasury.gov/resource-center/data-chart-center/"
        f"interest-rates/daily-treasury-rates.csv/{year}/all?"
        f"type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
    )
    print(f"  Fetching Treasury yields from Treasury.gov ({year})...")

    try:
        data = fetch_url(url)
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
        if not rows:
            raise ValueError("No rows in CSV")

        # Most recent row is first
        latest = rows[0]
        date_str = latest.get("Date", "")

        # Column names vary; try common patterns
        y10 = None
        y2 = None
        for key, val in latest.items():
            k = key.strip().lower()
            if "10 yr" in k or "10 year" in k or k == "10 yr":
                y10 = float(val)
            if "2 yr" in k or "2 year" in k or k == "2 yr":
                y2 = float(val)

        if y10 is None or y2 is None:
            # Fallback: try positional (columns are typically ordered by maturity)
            # Try explicit column names
            for key in latest:
                if "10" in key and ("Yr" in key or "Year" in key):
                    y10 = float(latest[key])
                if "2" in key and ("Yr" in key or "Year" in key) and "12" not in key and "20" not in key:
                    y2 = float(latest[key])

        if y10 is not None and y2 is not None:
            spread = round(y10 - y2, 4)
            print(f"  ✓ 10Y={y10}%, 2Y={y2}%, Spread={spread}%  ({date_str})")
            return {"value": spread, "y10": y10, "y2": y2, "date": date_str, "source": "Treasury.gov"}
    except Exception as e:
        print(f"  ✗ Treasury.gov failed: {e}")

    # Fallback: use Yahoo Finance for ^TNX (10Y) and ^IRX (13W) or compute from TLT/SHY
    return fetch_treasury_spread_yahoo()


def fetch_treasury_spread_yahoo():
    """Fallback: get yields from Yahoo Finance."""
    print("  Trying Yahoo Finance fallback for Treasury yields...")
    try:
        y10 = get_yahoo_price("^TNX")  # 10Y yield (quoted as e.g., 4.35)
        # ^IRX is 13-week, not 2Y. Try to approximate with ^FVX (5Y) or just use the 10Y level
        # For 2Y we can try to get it from a different source
        y2_data = get_yahoo_quote("^UST2Y")  # 2-year yield
        if y2_data:
            y2 = y2_data
        else:
            # Use a rough estimate: 2Y ≈ 10Y - historical_avg_spread
            y2 = y10 - 0.5  # rough fallback

        spread = round(y10 - y2, 4)
        print(f"  ✓ Yahoo fallback: 10Y≈{y10}%, 2Y≈{y2}%, Spread≈{spread}%")
        return {"value": spread, "y10": round(y10, 3), "y2": round(y2, 3),
                "date": datetime.date.today().isoformat(), "source": "Yahoo Finance (approx)"}
    except Exception as e:
        print(f"  ✗ Yahoo fallback also failed: {e}")
        return {"value": 0.46, "y10": 4.42, "y2": 3.96,
                "date": datetime.date.today().isoformat(), "source": "fallback"}


# ──────────────────────────────────────────────
# A: VIX from Yahoo Finance
# ──────────────────────────────────────────────
def fetch_vix():
    """Fetch latest VIX from Yahoo Finance public endpoint."""
    print("  Fetching VIX from Yahoo Finance...")
    try:
        price = get_yahoo_price("^VIX")
        print(f"  ✓ VIX = {price}")
        return {"value": round(price, 2), "date": datetime.date.today().isoformat(), "source": "Yahoo Finance"}
    except Exception as e:
        print(f"  ✗ VIX fetch failed: {e}")
        return {"value": 27.44, "date": datetime.date.today().isoformat(), "source": "fallback"}


# ──────────────────────────────────────────────
# C: Credit Spread (HYG yield - Treasury yield)
# ──────────────────────────────────────────────
def fetch_credit_spread(treasury_10y=4.4):
    """
    Approximate HY credit spread using HYG ETF yield minus risk-free rate.
    HYG SEC yield is typically around 7-8%, spread = HYG_yield - 10Y_Treasury.
    We approximate from HYG's dividend yield + price discount.
    """
    print("  Computing credit spread from HYG ETF data...")
    try:
        # Get HYG data from Yahoo Finance
        url = "https://query1.finance.yahoo.com/v8/finance/chart/HYG?interval=1d&range=5d"
        data = json.loads(fetch_url(url))
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice", 0)

        # HYG's approximate yield: annual dividend / price
        # HYG pays roughly $0.35/month = $4.20/year at par ~$80
        annual_div = 4.20  # approximate annual distribution
        hyg_yield = (annual_div / price) * 100 if price > 0 else 7.5

        spread = round(hyg_yield - treasury_10y, 2)
        spread = max(spread, 1.0)  # floor at 100bps (sanity check)
        print(f"  ✓ HYG price={price}, est yield={hyg_yield:.2f}%, spread={spread}%")
        return {"value": spread, "hyg_price": round(price, 2), "hyg_yield": round(hyg_yield, 2),
                "date": datetime.date.today().isoformat(), "source": "Yahoo Finance (HYG proxy)"}
    except Exception as e:
        print(f"  ✗ Credit spread computation failed: {e}")
        return {"value": 3.19, "date": datetime.date.today().isoformat(), "source": "fallback"}


# ──────────────────────────────────────────────
# O: Financial Stress / Outflow Pressure
# ──────────────────────────────────────────────
def fetch_outflow_pressure():
    """
    Composite financial stress indicator computed from:
    1. VIX term structure (VIX/VIX3M ratio) — backwardation = panic
    2. SPY drawdown from 52-week high
    3. Put/Call ratio proxy from market breadth

    Output: 0-100 scale where higher = more stress/outflow.
    """
    print("  Computing financial stress composite...")
    stress_score = 30  # neutral default
    components = {}

    # 1) VIX term structure
    try:
        vix = get_yahoo_price("^VIX")
        vix3m = get_yahoo_price("^VIX3M")
        if vix3m > 0:
            ratio = vix / vix3m
            # ratio > 1 = backwardation (panic), < 1 = contango (calm)
            # Map: 0.7→5, 0.85→15, 1.0→35, 1.1→55, 1.2→75, 1.4→95
            if ratio <= 0.7:
                vix_stress = 5
            elif ratio <= 0.85:
                vix_stress = 5 + (ratio - 0.7) / 0.15 * 10
            elif ratio <= 1.0:
                vix_stress = 15 + (ratio - 0.85) / 0.15 * 20
            elif ratio <= 1.1:
                vix_stress = 35 + (ratio - 1.0) / 0.1 * 20
            elif ratio <= 1.2:
                vix_stress = 55 + (ratio - 1.1) / 0.1 * 20
            else:
                vix_stress = min(75 + (ratio - 1.2) / 0.2 * 20, 100)
            components["vix_ratio"] = round(ratio, 3)
            components["vix_stress"] = round(vix_stress, 1)
            print(f"    VIX/VIX3M ratio = {ratio:.3f} → stress = {vix_stress:.1f}")
    except Exception as e:
        vix_stress = 30
        print(f"    VIX term structure failed: {e}")

    # 2) SPY drawdown from 52-week high
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1d&range=1y"
        data = json.loads(fetch_url(url))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        high_52w = max(closes)
        current = closes[-1]
        drawdown = (high_52w - current) / high_52w * 100
        # Map: 0%→5, 5%→20, 10%→40, 15%→60, 20%→80, 30%→95
        if drawdown <= 2:
            dd_stress = 5
        elif drawdown <= 5:
            dd_stress = 5 + (drawdown - 2) / 3 * 15
        elif drawdown <= 10:
            dd_stress = 20 + (drawdown - 5) / 5 * 20
        elif drawdown <= 15:
            dd_stress = 40 + (drawdown - 10) / 5 * 20
        elif drawdown <= 20:
            dd_stress = 60 + (drawdown - 15) / 5 * 20
        else:
            dd_stress = min(80 + (drawdown - 20) / 10 * 15, 100)
        components["drawdown_pct"] = round(drawdown, 2)
        components["drawdown_stress"] = round(dd_stress, 1)
        components["spy_current"] = round(current, 2)
        components["spy_52w_high"] = round(high_52w, 2)
        print(f"    SPY drawdown = {drawdown:.2f}% from 52w high → stress = {dd_stress:.1f}")
    except Exception as e:
        dd_stress = 30
        print(f"    SPY drawdown calc failed: {e}")

    # 3) Market breadth proxy: recent weekly performance
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?interval=1wk&range=1mo"
        data = json.loads(fetch_url(url))
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) >= 2:
            weekly_ret = (closes[-1] - closes[-2]) / closes[-2] * 100
            # Negative weekly returns indicate selling pressure
            if weekly_ret >= 2:
                breadth_stress = 5
            elif weekly_ret >= 0:
                breadth_stress = 10 + (2 - weekly_ret) / 2 * 15
            elif weekly_ret >= -2:
                breadth_stress = 25 + (-weekly_ret) / 2 * 20
            elif weekly_ret >= -5:
                breadth_stress = 45 + (-weekly_ret - 2) / 3 * 25
            else:
                breadth_stress = min(70 + (-weekly_ret - 5) / 5 * 30, 100)
            components["weekly_return"] = round(weekly_ret, 2)
            components["breadth_stress"] = round(breadth_stress, 1)
            print(f"    Weekly return = {weekly_ret:.2f}% → stress = {breadth_stress:.1f}")
        else:
            breadth_stress = 30
    except Exception as e:
        breadth_stress = 30
        print(f"    Breadth calc failed: {e}")

    # Composite: weighted average
    stress_score = round(vix_stress * 0.4 + dd_stress * 0.35 + breadth_stress * 0.25, 1)
    stress_score = max(0, min(100, stress_score))
    components["composite"] = stress_score
    print(f"  ✓ Outflow/Stress composite = {stress_score}")

    return {
        "value": stress_score,
        "components": components,
        "date": datetime.date.today().isoformat(),
        "source": "Composite (VIX term structure + SPY drawdown + breadth)"
    }


# ──────────────────────────────────────────────
# Yahoo Finance helpers
# ──────────────────────────────────────────────
def get_yahoo_price(symbol):
    """Get latest price from Yahoo Finance public chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    data = json.loads(fetch_url(url))
    result = data["chart"]["result"][0]
    return result["meta"]["regularMarketPrice"]


def get_yahoo_quote(symbol):
    """Try to get quote from Yahoo Finance."""
    try:
        price = get_yahoo_price(symbol)
        return price
    except:
        return None


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("🌮 TACO Stress Index — Data Fetcher")
    print(f"   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # 1. Treasury Spread
    print("\n[T] Treasury Spread")
    t_data = fetch_treasury_spread()

    # 2. VIX
    print("\n[A] Anxiety / VIX")
    a_data = fetch_vix()

    # 3. Credit Spread
    print("\n[C] Credit Spread")
    treasury_10y = t_data.get("y10", 4.4)
    c_data = fetch_credit_spread(treasury_10y)

    # 4. Outflow Pressure
    print("\n[O] Outflow / Financial Stress")
    o_data = fetch_outflow_pressure()

    # Compute TACO scores
    t_bps = t_data["value"] * 100  # convert to bps
    t_th = [(-100,100),(-50,80),(0,60),(50,40),(150,20),(300,0)]
    t_score = interp(t_bps, t_th)

    a_val = a_data["value"]
    a_th = [(10,0),(20,20),(30,50),(40,70),(50,85),(80,100)]
    a_score = interp(a_val, a_th)

    c_bps = c_data["value"] * 100
    c_th = [(100,0),(300,20),(500,50),(700,70),(900,85),(1200,100)]
    c_score = interp(c_bps, c_th)

    o_val = o_data["value"]  # already 0-100
    o_score = max(0, min(100, o_val))

    total = t_score * 0.25 + a_score * 0.30 + c_score * 0.25 + o_score * 0.20

    # Build output
    output = {
        "taco_score": round(total, 1),
        "updated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "components": {
            "T": {**t_data, "score": round(t_score, 1), "weight": 0.25,
                  "display": f"{'+' if t_data['value'] >= 0 else ''}{t_data['value']:.2f}%"},
            "A": {**a_data, "score": round(a_score, 1), "weight": 0.30,
                  "display": f"{a_data['value']:.2f}"},
            "C": {**c_data, "score": round(c_score, 1), "weight": 0.25,
                  "display": f"{c_data['value']:.2f}%"},
            "O": {**o_data, "score": round(o_score, 1), "weight": 0.20,
                  "display": f"{o_data['value']:.1f}/100"},
        },
        "scores": {
            "T": round(t_score, 1),
            "A": round(a_score, 1),
            "C": round(c_score, 1),
            "O": round(o_score, 1),
        }
    }

    # Determine signal
    if total >= 85:
        output["signal"] = {"level": "extreme", "zh": "TACO 爆辣模式", "action": "全力抄底"}
    elif total >= 70:
        output["signal"] = {"level": "high", "zh": "TACO 重辣模式", "action": "積極佈局"}
    elif total >= 50:
        output["signal"] = {"level": "medium", "zh": "TACO 微辣模式", "action": "觀察等待"}
    elif total >= 30:
        output["signal"] = {"level": "low", "zh": "TACO 原味模式", "action": "中性偏空"}
    else:
        output["signal"] = {"level": "cool", "zh": "TACO 冰鎮模式", "action": "市場過熱"}

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(script_dir, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"🌮 TACO Score: {total:.1f} — {output['signal']['zh']}")
    print(f"   T={t_score:.1f}  A={a_score:.1f}  C={c_score:.1f}  O={o_score:.1f}")
    print(f"   Saved to {out_path}")
    print("=" * 60)

    return 0


def interp(val, thresholds):
    """Piecewise linear interpolation."""
    if val <= thresholds[0][0]:
        return thresholds[0][1]
    if val >= thresholds[-1][0]:
        return thresholds[-1][1]
    for i in range(len(thresholds) - 1):
        v1, s1 = thresholds[i]
        v2, s2 = thresholds[i + 1]
        if v1 <= val <= v2:
            r = (val - v1) / (v2 - v1)
            return s1 + r * (s2 - s1)
    return 50


if __name__ == "__main__":
    sys.exit(main())
