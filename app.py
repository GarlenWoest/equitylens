"""Streamlit front end: type a ticker, get a valuation.

    streamlit run app.py

Pulls fundamentals live from SEC EDGAR; market inputs come from
data/assumptions.json (edit beta/price there or override in the sidebar).
"""
import sys
sys.path.insert(0, "src")

import streamlit as st

from dcf import load_assumptions, run_dcf
from edgar_client import latest_years
import comps as comps_mod
import simulate as sim

st.set_page_config(page_title="EquityLens", layout="wide")
st.title("EquityLens — DCF & comparables")

ticker = st.text_input("Ticker", "AAPL").strip().upper()
a = load_assumptions()

with st.sidebar:
    st.header("Assumptions")
    a["market"]["risk_free"] = st.number_input("Risk-free rate", value=a["market"]["risk_free"], format="%.3f")
    a["market"]["equity_risk_premium"] = st.number_input("Equity risk premium", value=a["market"]["equity_risk_premium"], format="%.3f")
    a["projection"]["terminal_growth"] = st.number_input("Terminal growth", value=a["projection"]["terminal_growth"], format="%.3f")
    tk = a["tickers"].setdefault(ticker, {"beta": 1.0, "price": None})
    tk["beta"] = st.number_input("Beta", value=float(tk.get("beta", 1.0)))
    tk["price"] = st.number_input("Current price", value=float(tk.get("price") or 0.0)) or None

if st.button("Value it") or ticker:
    try:
        company, rows = latest_years(ticker, n=5)
        d = run_dcf(company, ticker, rows, a)
        cmp = comps_mod.implied_values(ticker, rows, comps_mod.load_peers())
        mc = sim.monte_carlo(rows, a, d["wacc"], d["terminal_growth"], n=4000)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("DCF value / share", f"${d['value_per_share']:,.0f}")
        c2.metric("Current price", f"${d['market_price']:,.0f}" if d["market_price"] else "—")
        if d["upside"] is not None:
            c3.metric("Upside vs price", f"{d['upside']:+.0%}")
        c4.metric("WACC", f"{d['wacc']:.1%}")

        st.subheader(f"{company}")
        st.write(f"Enterprise value **${d['enterprise_value']/1e9:,.0f}B**, "
                 f"equity value **${d['equity_value']/1e9:,.0f}B**, "
                 f"{d['pct_value_in_terminal']:.0%} of value in the terminal.")
        st.write(f"Monte Carlo P10–P90: **${mc['p10']:,.0f} – ${mc['p90']:,.0f}**")
        if cmp:
            st.write(f"Comps imply **${cmp['low']:,.0f} – ${cmp['high']:,.0f}** per share.")
    except Exception as e:
        st.error(f"Couldn't value {ticker}: {e}")
