"""Unit tests for the DCF math -- these don't touch the network, they check the
formulas against hand-computed values."""
import os
import sys

sys.path.insert(0, "src")
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from dcf import cost_of_equity, wacc, value_per_share


def test_capm():
    # 4% risk-free + beta 1.0 * 5% premium = 9%
    assert abs(cost_of_equity(0.04, 1.0, 0.05) - 0.09) < 1e-9


def test_wacc_all_equity():
    # no debt -> WACC equals cost of equity
    assert abs(wacc(1000, 0, 0.09, 0.05, 0.21) - 0.09) < 1e-9


def test_wacc_blend():
    # 50/50 capital structure, after-tax cost of debt applied
    w = wacc(500, 500, 0.10, 0.05, 0.20)
    expected = 0.5 * 0.10 + 0.5 * 0.05 * (1 - 0.20)
    assert abs(w - expected) < 1e-9


def _toy_rows():
    # flat company: $1,000 revenue, 20% EBIT margin, no D&A/capex/NWC swings
    base = {"revenue": 1000.0, "operating_income": 200.0, "d_and_a": 0.0,
            "capex": 0.0, "current_assets": 0.0, "current_liabilities": 0.0,
            "cash": 0.0, "long_term_debt": 0.0, "short_term_debt": 0.0,
            "diluted_shares": 100.0, "tax_expense": 42.0, "pretax_income": 200.0}
    return [dict(base) for _ in range(3)]


def test_zero_growth_matches_perpetuity():
    # With 0% growth, tax 21%, FCF is constant = 200*(1-0.21)=158 per year.
    # Value should sit near the Gordon perpetuity FCF*(1+g)/(w-g) discounted.
    rows = _toy_rows()
    assumptions = {"projection": {"years": 5, "terminal_growth": 0.0,
                                  "cost_of_debt": 0.05, "fade_to_terminal": False}}
    ps = value_per_share(rows, assumptions, 0.10, 0.0, growth_mult=0.0)
    # Constant FCF 158, WACC 10%, g 0 -> perpetuity value 1580 / 100 shares = ~15.8
    assert 14 < ps < 18


def test_higher_wacc_lowers_value():
    rows = _toy_rows()
    a = {"projection": {"years": 5, "terminal_growth": 0.02,
                        "cost_of_debt": 0.05, "fade_to_terminal": False}}
    low = value_per_share(rows, a, 0.08, 0.02, growth_mult=0.0)
    high = value_per_share(rows, a, 0.12, 0.02, growth_mult=0.0)
    assert high < low


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
