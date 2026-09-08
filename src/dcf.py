"""Unlevered DCF: project free cash flow, discount at WACC, bridge to per share.

The projection is driven off the company's own recent history (margins, capex,
D&A and working-capital as a share of revenue), so you're not hand-waving inputs.
Growth fades from the recent trend down to the terminal rate.
"""
import json

import numpy as np

ASSUMPTIONS = "data/assumptions.json"


def load_assumptions(path=ASSUMPTIONS):
    return json.load(open(path))


def _avg_ratio(rows, num, den, n=3):
    """Average of num/den over the last n years where both exist."""
    vals = [r[num] / r[den] for r in rows[-n:]
            if r.get(num) is not None and r.get(den)]
    return float(np.mean(vals)) if vals else 0.0


def _hist_growth(rows):
    revs = [r["revenue"] for r in rows if r.get("revenue")]
    if len(revs) < 2:
        return 0.04
    cagr = (revs[-1] / revs[0]) ** (1 / (len(revs) - 1)) - 1
    return float(np.clip(cagr, 0.0, 0.15))     # keep it sane


def cost_of_equity(rf, beta, erp):
    return rf + beta * erp                       # CAPM


def wacc(equity_value, debt, coe, cost_debt, tax_rate):
    v = equity_value + debt
    if v <= 0:
        return coe
    we, wd = equity_value / v, debt / v
    return we * coe + wd * cost_debt * (1 - tax_rate)


def growth_path(rows, years, terminal_g, fade=True):
    start = _hist_growth(rows)
    if not fade:
        return [start] * years
    # linear fade from the recent growth rate down to terminal growth
    return list(np.linspace(start, terminal_g, years))


def project_fcf(rows, assumptions, market_price=None, beta=None):
    a = assumptions
    proj = a["projection"]
    years = proj["years"]
    base_rev = rows[-1]["revenue"]

    ebit_margin = _avg_ratio(rows, "operating_income", "revenue")
    da_pct = _avg_ratio(rows, "d_and_a", "revenue")
    capex_pct = _avg_ratio(rows, "capex", "revenue")
    tax_rate = _effective_tax(rows)
    nwc_pct = _nwc_pct(rows)

    growth = growth_path(rows, years, proj["terminal_growth"], proj["fade_to_terminal"])

    schedule, rev = [], base_rev
    prev_nwc = nwc_pct * base_rev
    for i, g in enumerate(growth):
        rev = rev * (1 + g)
        ebit = rev * ebit_margin
        nopat = ebit * (1 - tax_rate)
        da = rev * da_pct
        capex = rev * capex_pct
        nwc = rev * nwc_pct
        d_nwc = nwc - prev_nwc
        prev_nwc = nwc
        fcf = nopat + da - capex - d_nwc
        schedule.append({"year": i + 1, "revenue": rev, "ebit": ebit,
                         "nopat": nopat, "da": da, "capex": capex,
                         "d_nwc": d_nwc, "fcf": fcf})
    drivers = {"ebit_margin": ebit_margin, "da_pct": da_pct,
               "capex_pct": capex_pct, "tax_rate": tax_rate,
               "nwc_pct": nwc_pct, "growth": growth}
    return schedule, drivers


def _effective_tax(rows):
    pairs = [(r["tax_expense"], r["pretax_income"]) for r in rows[-3:]
             if r.get("tax_expense") is not None and r.get("pretax_income")]
    rates = [t / p for t, p in pairs if p > 0]
    r = float(np.mean(rates)) if rates else 0.21
    return float(np.clip(r, 0.10, 0.35))


def _nwc_pct(rows):
    vals = []
    for r in rows[-3:]:
        ca, cl = r.get("current_assets"), r.get("current_liabilities")
        if ca is not None and cl is not None and r.get("revenue"):
            vals.append((ca - cl) / r["revenue"])
    return float(np.mean(vals)) if vals else 0.0


def net_debt(rows):
    last = rows[-1]
    debt = (last.get("long_term_debt") or 0) + (last.get("short_term_debt") or 0)
    cash = last.get("cash") or 0
    return debt - cash, debt, cash


def value_per_share(rows, assumptions, wacc_, terminal_g,
                    growth_mult=1.0, margin_delta=0.0):
    """Re-run the DCF math with explicit WACC/terminal growth and optional
    tweaks to growth and margin. Used by the sensitivity + Monte Carlo layer."""
    proj = assumptions["projection"]
    years = proj["years"]
    base_rev = rows[-1]["revenue"]
    ebit_margin = _avg_ratio(rows, "operating_income", "revenue") + margin_delta
    da_pct = _avg_ratio(rows, "d_and_a", "revenue")
    capex_pct = _avg_ratio(rows, "capex", "revenue")
    tax = _effective_tax(rows)
    nwc_pct = _nwc_pct(rows)
    growth = [g * growth_mult
              for g in growth_path(rows, years, terminal_g, proj["fade_to_terminal"])]

    rev, prev_nwc, fcfs = base_rev, nwc_pct * base_rev, []
    for g in growth:
        rev *= (1 + g)
        nopat = rev * ebit_margin * (1 - tax)
        nwc = rev * nwc_pct
        fcfs.append(nopat + rev * da_pct - rev * capex_pct - (nwc - prev_nwc))
        prev_nwc = nwc

    fcfs = np.array(fcfs)
    disc = np.array([(1 + wacc_) ** -(i + 1) for i in range(years)])
    if wacc_ <= terminal_g:
        return np.nan
    tv = fcfs[-1] * (1 + terminal_g) / (wacc_ - terminal_g)
    ev = float((fcfs * disc).sum() + tv * disc[-1])
    nd, _, _ = net_debt(rows)
    return (ev - nd) / rows[-1]["diluted_shares"]


def run_dcf(company, ticker, rows, assumptions):
    a = assumptions
    tk = a["tickers"].get(ticker.upper(), {})
    beta = tk.get("beta", 1.0)
    price = tk.get("price")
    rf = a["market"]["risk_free"]
    erp = a["market"]["equity_risk_premium"]
    term_g = a["projection"]["terminal_growth"]
    cost_debt = a["projection"]["cost_of_debt"]

    schedule, drivers = project_fcf(rows, assumptions)
    nd, debt, cash = net_debt(rows)
    shares = rows[-1]["diluted_shares"]

    coe = cost_of_equity(rf, beta, erp)
    # market cap uses the input price if given, else book equity proxy
    equity_mktval = (price * shares) if price else max(rows[-1]["revenue"], 1)
    w = wacc(equity_mktval, debt, coe, cost_debt, drivers["tax_rate"])

    fcfs = np.array([s["fcf"] for s in schedule])
    disc = np.array([(1 + w) ** -(i + 1) for i in range(len(fcfs))])
    pv_fcf = float((fcfs * disc).sum())

    tv = fcfs[-1] * (1 + term_g) / (w - term_g)      # Gordon growth
    pv_tv = float(tv * disc[-1])

    ev = pv_fcf + pv_tv
    equity_val = ev - nd
    per_share = equity_val / shares
    upside = (per_share / price - 1) if price else None

    return {
        "company": company, "ticker": ticker.upper(),
        "wacc": w, "cost_of_equity": coe, "terminal_growth": term_g,
        "schedule": schedule, "drivers": drivers,
        "pv_fcf": pv_fcf, "pv_terminal": pv_tv, "terminal_value": tv,
        "enterprise_value": ev, "net_debt": nd, "equity_value": equity_val,
        "shares": shares, "value_per_share": per_share,
        "market_price": price, "upside": upside,
        "pct_value_in_terminal": pv_tv / ev if ev else None,
    }
