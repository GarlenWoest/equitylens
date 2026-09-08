"""Turn the single DCF number into a range: a WACC x terminal-growth sensitivity
grid, a Monte Carlo distribution, a driver tornado, and a reverse-DCF that backs
out the growth the current price implies.
"""
import numpy as np

from dcf import growth_path, value_per_share

RNG = np.random.default_rng(7)


def sensitivity(rows, assumptions, base_wacc, base_g, span=0.015, steps=5):
    waccs = np.linspace(base_wacc - span, base_wacc + span, steps)
    gs = np.linspace(base_g - 0.01, base_g + 0.01, steps)
    grid = np.array([[value_per_share(rows, assumptions, w, g)
                      for g in gs] for w in waccs])
    return {"wacc": waccs, "growth": gs, "value": grid}


def monte_carlo(rows, assumptions, base_wacc, base_g, n=10000):
    # sample the assumptions we're least sure about, around the base case
    wacc = RNG.normal(base_wacc, 0.007, n)
    g = RNG.normal(base_g, 0.004, n)
    growth_mult = RNG.normal(1.0, 0.15, n)
    margin_delta = RNG.normal(0.0, 0.015, n)
    vals = np.array([value_per_share(rows, assumptions, w, gg, gm, md)
                     for w, gg, gm, md in zip(wacc, g, growth_mult, margin_delta)])
    vals = vals[np.isfinite(vals) & (vals > 0)]
    return {
        "values": vals,
        "p10": float(np.percentile(vals, 10)),
        "p50": float(np.percentile(vals, 50)),
        "p90": float(np.percentile(vals, 90)),
        "mean": float(vals.mean()),
    }


def tornado(rows, assumptions, base_wacc, base_g):
    base = value_per_share(rows, assumptions, base_wacc, base_g)
    drivers = {
        "WACC (+/-1pt)": [value_per_share(rows, assumptions, base_wacc + 0.01, base_g),
                          value_per_share(rows, assumptions, base_wacc - 0.01, base_g)],
        "Terminal growth (+/-0.5pt)": [value_per_share(rows, assumptions, base_wacc, base_g - 0.005),
                                       value_per_share(rows, assumptions, base_wacc, base_g + 0.005)],
        "Revenue growth (+/-20%)": [value_per_share(rows, assumptions, base_wacc, base_g, growth_mult=0.8),
                                    value_per_share(rows, assumptions, base_wacc, base_g, growth_mult=1.2)],
        "EBIT margin (+/-2pt)": [value_per_share(rows, assumptions, base_wacc, base_g, margin_delta=-0.02),
                                 value_per_share(rows, assumptions, base_wacc, base_g, margin_delta=0.02)],
    }
    rows_out = []
    for name, (lo, hi) in drivers.items():
        rows_out.append({"driver": name, "low": lo, "high": hi,
                         "swing": abs(hi - lo)})
    rows_out.sort(key=lambda d: d["swing"], reverse=True)
    return {"base": base, "drivers": rows_out}


def implied_wacc(rows, assumptions, base_g, price, lo=0.03, hi=0.25):
    """Reverse DCF: what discount rate makes the DCF equal today's price?
    Value falls as WACC rises, so we bisect for the crossing."""
    if not price:
        return None
    f = lambda w: value_per_share(rows, assumptions, w, base_g) - price
    if f(lo) < 0 or f(hi) > 0:          # price outside the solvable band
        return {"reachable": False, "wacc": None}
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(mid) > 0:                  # value too high -> need a higher WACC
            lo = mid
        else:
            hi = mid
    return {"reachable": True, "wacc": (lo + hi) / 2}


def implied_growth(rows, assumptions, base_wacc, base_g, price):
    """Reverse DCF: what revenue-growth multiple would justify today's price?
    Solve value(growth_mult) = price by bisection."""
    if not price:
        return None
    f = lambda mult: value_per_share(rows, assumptions, base_wacc, base_g, growth_mult=mult) - price
    lo, hi = 0.0, 6.0
    if f(hi) < 0:                       # even very high growth can't reach price
        return {"reachable": False, "growth_mult": None}
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    mult = (lo + hi) / 2
    years = assumptions["projection"]["years"]
    base_avg = float(np.mean(growth_path(rows, years, base_g, True)))
    return {"reachable": True, "growth_mult": mult,
            "implied_avg_growth": base_avg * mult}
