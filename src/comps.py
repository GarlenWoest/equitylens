"""Trading comparables: apply peer median multiples to the target's own metrics
to imply a value range, as a cross-check on the DCF.

Peer multiples come from data/peers.json (a dated snapshot -- see the note there).
"""
import json

import numpy as np

from dcf import net_debt

PEERS = "data/peers.json"


def load_peers(path=PEERS):
    return json.load(open(path))


def target_metrics(rows):
    last = rows[-1]
    ebitda = (last["operating_income"] or 0) + (last["d_and_a"] or 0)
    nd, _, _ = net_debt(rows)
    return {
        "revenue": last["revenue"],
        "ebitda": ebitda,
        "net_income": last.get("net_income") or 0,
        "net_debt": nd,
        "shares": last["diluted_shares"],
    }


def implied_values(ticker, rows, peers_data):
    peers = peers_data.get(ticker.upper(), [])
    if not peers:
        return None
    m = target_metrics(rows)

    def med(key):
        return float(np.median([p[key] for p in peers]))

    out = {}
    # EV/EBITDA -> EV -> equity -> per share
    ev = med("ev_ebitda") * m["ebitda"]
    out["EV/EBITDA"] = (ev - m["net_debt"]) / m["shares"]
    # EV/Sales -> EV -> equity -> per share
    ev_s = med("ev_sales") * m["revenue"]
    out["EV/Sales"] = (ev_s - m["net_debt"]) / m["shares"]
    # P/E -> equity directly -> per share
    out["P/E"] = (med("pe") * m["net_income"]) / m["shares"]

    vals = list(out.values())
    return {
        "per_share_by_multiple": out,
        "low": float(min(vals)),
        "median": float(np.median(vals)),
        "high": float(max(vals)),
        "peer_medians": {k: med(k) for k in ["ev_ebitda", "pe", "ev_sales"]},
        "n_peers": len(peers),
    }


def target_own_multiples(rows, price):
    """Where the target itself trades, to compare against peers."""
    if not price:
        return None
    m = target_metrics(rows)
    equity = price * m["shares"]
    ev = equity + m["net_debt"]
    return {
        "ev_ebitda": ev / m["ebitda"] if m["ebitda"] else None,
        "pe": equity / m["net_income"] if m["net_income"] else None,
        "ev_sales": ev / m["revenue"] if m["revenue"] else None,
    }
