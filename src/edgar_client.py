"""Pull annual financials from SEC EDGAR's XBRL API and cache them locally.

SEC asks every automated caller to send a User-Agent with contact info -- put
your own email in CONTACT below before hammering the API. Fundamentals here are
the real numbers from a company's 10-K; market inputs (price, beta) live in the
assumptions config instead, since EDGAR doesn't carry them.
"""
import json
import os
import re
import time
import warnings

# LibreSSL on stock macOS python triggers a noisy urllib3 warning; it's harmless.
# Filter must run before requests/urllib3 is imported.
warnings.filterwarnings("ignore", message=".*OpenSSL.*")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")

import requests  # noqa: E402

CONTACT = "research@example.com"        # <- put your email here
HEADERS = {"User-Agent": f"EquityLens (contact: {CONTACT})"}
CACHE_DIR = "data/cache"
TICKER_MAP = "data/cache/ticker_cik.json"

# Each line maps to the XBRL tags we'll try, in order. Companies don't all use
# the same tag, so we fall back until one has data.
LINES = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "d_and_a": ["DepreciationDepletionAndAmortization",
                "DepreciationAmortizationAndAccretionNet",
                "DepreciationAndAmortization",
                "DepreciationAmortizationAndOther",
                "Depreciation"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "tax_expense": ["IncomeTaxExpenseBenefit"],
    "pretax_income": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "short_term_debt": ["LongTermDebtCurrent", "DebtCurrent"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    time.sleep(0.2)   # be polite to SEC
    return r.json()


def _ticker_to_cik(ticker):
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(TICKER_MAP):
        data = _get("https://www.sec.gov/files/company_tickers.json")
        with open(TICKER_MAP, "w") as f:
            json.dump(data, f)
    else:
        data = json.load(open(TICKER_MAP))
    for row in data.values():
        if row["ticker"].upper() == ticker.upper():
            return str(row["cik_str"]).zfill(10)
    raise ValueError(f"ticker {ticker} not found in SEC list")


def _annual(concept):
    """Return {fiscal_year: value} using SEC's calendar 'frame' field.
    Flow items are framed CY2024, balance items CY2024Q4I -- we accept both."""
    out = {}
    for unit_key, rows in concept["units"].items():
        for x in rows:
            m = re.fullmatch(r"CY(\d{4})(Q4I)?", x.get("frame", ""))
            if m:
                out[int(m.group(1))] = x["val"]
    return out


def fetch_facts(ticker, refresh=False):
    """Fetch and cache the annual lines we need for a valuation."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = f"{CACHE_DIR}/{ticker.upper()}.json"
    if os.path.exists(cache) and not refresh:
        return json.load(open(cache))

    cik = _ticker_to_cik(ticker)
    facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
    gaap = facts["facts"]["us-gaap"]

    series = {}
    for line, tags in LINES.items():
        for tag in tags:
            if tag in gaap:
                s = _annual(gaap[tag])
                if s:
                    series[line] = s
                    break
        series.setdefault(line, {})

    result = {"ticker": ticker.upper(), "company": facts.get("entityName", ticker),
              "cik": cik, "series": series}
    with open(cache, "w") as f:
        json.dump(result, f, indent=2)
    return result


def latest_years(ticker, n=5, refresh=False):
    """Return the most recent n fiscal years as a list of dicts (oldest first)."""
    facts = fetch_facts(ticker, refresh=refresh)
    s = facts["series"]
    years = sorted(set().union(*[set(v) for v in s.values() if v]))[-n:]
    rows = []
    for y in years:
        row = {"year": y}
        for line, vals in s.items():
            row[line] = vals.get(y)
        rows.append(row)
    return facts["company"], rows


if __name__ == "__main__":
    import sys
    tkr = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    name, rows = latest_years(tkr, refresh=True)
    print(f"{name} ({tkr}) — last {len(rows)} fiscal years")
    for r in rows:
        rev = r["revenue"] / 1e9 if r["revenue"] else 0
        ebit = r["operating_income"] / 1e9 if r["operating_income"] else 0
        print(f"  FY{r['year']}: revenue ${rev:,.1f}B  operating income ${ebit:,.1f}B")
