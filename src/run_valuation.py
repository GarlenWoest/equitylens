"""Value a ticker end to end and write the charts + a JSON summary.

    python src/run_valuation.py AAPL
"""
import json
import os
import sys

import comps as comps_mod
import simulate as sim
import viz
from dcf import load_assumptions, run_dcf
from edgar_client import latest_years


def value(ticker, refresh=False):
    a = load_assumptions()
    company, rows = latest_years(ticker, n=5, refresh=refresh)

    dcf = run_dcf(company, ticker, rows, a)
    peers = comps_mod.load_peers()
    cmp = comps_mod.implied_values(ticker, rows, peers)
    own_mult = comps_mod.target_own_multiples(rows, dcf["market_price"])

    base_w, base_g = dcf["wacc"], dcf["terminal_growth"]
    sens = sim.sensitivity(rows, a, base_w, base_g)
    mc = sim.monte_carlo(rows, a, base_w, base_g)
    tor = sim.tornado(rows, a, base_w, base_g)
    imp_wacc = sim.implied_wacc(rows, a, base_g, dcf["market_price"])

    return {"rows": rows, "dcf": dcf, "comps": cmp, "own_multiples": own_mult,
            "sensitivity": sens, "mc": mc, "tornado": tor, "implied_wacc": imp_wacc}


def _summary(ticker, r):
    d, mc, cmp = r["dcf"], r["mc"], r["comps"]
    out = {
        "ticker": ticker.upper(), "company": d["company"],
        "wacc": round(d["wacc"], 4), "cost_of_equity": round(d["cost_of_equity"], 4),
        "terminal_growth": d["terminal_growth"],
        "enterprise_value_bn": round(d["enterprise_value"] / 1e9, 1),
        "equity_value_bn": round(d["equity_value"] / 1e9, 1),
        "dcf_value_per_share": round(d["value_per_share"], 2),
        "market_price": d["market_price"],
        "upside_vs_price": round(d["upside"], 4) if d["upside"] is not None else None,
        "pct_value_in_terminal": round(d["pct_value_in_terminal"], 3),
        "mc_p10": round(mc["p10"], 2), "mc_p50": round(mc["p50"], 2),
        "mc_p90": round(mc["p90"], 2),
        "ebit_margin": round(d["drivers"]["ebit_margin"], 4),
        "effective_tax": round(d["drivers"]["tax_rate"], 4),
    }
    if cmp:
        out["comps_low"] = round(cmp["low"], 2)
        out["comps_median"] = round(cmp["median"], 2)
        out["comps_high"] = round(cmp["high"], 2)
    if r["implied_wacc"] and r["implied_wacc"].get("reachable"):
        out["market_implied_wacc"] = round(r["implied_wacc"]["wacc"], 4)
    return out


def main():
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "AAPL").upper()
    refresh = "--refresh" in sys.argv
    os.makedirs("examples", exist_ok=True)

    r = value(ticker, refresh=refresh)
    d = r["dcf"]

    viz.football_field(ticker, d["value_per_share"], r["mc"], r["comps"],
                       d["market_price"])
    viz.sensitivity_heatmap(ticker, r["sensitivity"], d["market_price"])
    viz.monte_carlo_hist(ticker, r["mc"], d["market_price"])
    viz.tornado_chart(ticker, r["tornado"])

    summary = _summary(ticker, r)
    with open(f"examples/{ticker}_valuation.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n===== {summary['company']} ({ticker}) =====")
    print(json.dumps(summary, indent=2))
    print(f"\ncharts -> assets/   summary -> examples/{ticker}_valuation.json")


if __name__ == "__main__":
    main()
