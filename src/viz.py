"""Charts for the README and the memo (matplotlib, static PNGs)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

ASSETS = "assets"
NAVY = "#14233A"
SLATE = "#5B6B7E"
TEAL = "#12727A"
GOLD = "#C08A2D"
RED = "#B0453A"
GREEN = "#2E7D5B"
GRID = "#E3E7EC"

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130,
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.edgecolor": GRID, "axes.labelcolor": NAVY, "axes.titlecolor": NAVY,
    "text.color": NAVY, "xtick.color": SLATE, "ytick.color": SLATE,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def _save(fig, name):
    fig.tight_layout()
    p = f"{ASSETS}/{name}"
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return p


def football_field(ticker, dcf_base, mc, comps, price):
    """Horizontal value ranges: DCF (Monte Carlo band), comps, and DCF base,
    with the current price marked."""
    bars = []
    bars.append(("DCF — Monte Carlo P10–P90", mc["p10"], mc["p90"], TEAL))
    if comps:
        bars.append(("Trading comps (low–high)", comps["low"], comps["high"], GOLD))
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for i, (label, lo, hi, color) in enumerate(bars):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=color, alpha=0.85,
                edgecolor="white")
        ax.text(lo, i + 0.34, f"${lo:,.0f}", va="center", ha="left",
                fontsize=9, color=SLATE)
        ax.text(hi, i + 0.34, f"${hi:,.0f}", va="center", ha="right",
                fontsize=9, color=SLATE)
    ax.scatter([dcf_base], [0], color=NAVY, zorder=5, s=40)
    ax.text(dcf_base, -0.36, f"DCF base ${dcf_base:,.0f}", ha="center",
            fontsize=8.5, color=NAVY)
    if price:
        ax.axvline(price, color=RED, lw=1.8, ls="--")
        ax.text(price, len(bars) - 0.3, f" current ${price:,.0f}", color=RED,
                fontsize=9.5, fontweight="bold", va="top")
    ax.set_yticks(range(len(bars)))
    ax.set_yticklabels([b[0] for b in bars])
    ax.set_ylim(-0.7, len(bars) - 0.2)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_title(f"{ticker} — valuation football field (per share)",
                 fontsize=13, fontweight="bold", loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, f"01_football_field_{ticker}.png")


def sensitivity_heatmap(ticker, sens, price):
    v = sens["value"]
    fig, ax = plt.subplots(figsize=(7.6, 5))
    im = ax.imshow(v, cmap="BuPu", aspect="auto", origin="lower")
    ax.set_xticks(range(len(sens["growth"])))
    ax.set_xticklabels([f"{g:.1%}" for g in sens["growth"]])
    ax.set_yticks(range(len(sens["wacc"])))
    ax.set_yticklabels([f"{w:.1%}" for w in sens["wacc"]])
    ax.set_xlabel("Terminal growth")
    ax.set_ylabel("WACC")
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            val = v[i, j]
            near = price and abs(val - price) / price < 0.05
            ax.text(j, i, f"${val:,.0f}", ha="center", va="center",
                    fontsize=8.5,
                    color="white" if val > np.nanmean(v) else NAVY,
                    fontweight="bold" if near else "normal")
    ax.set_title(f"{ticker} — value/share sensitivity", fontsize=13,
                 fontweight="bold", loc="left")
    return _save(fig, f"02_sensitivity_{ticker}.png")


def monte_carlo_hist(ticker, mc, price):
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.hist(mc["values"], bins=45, color=TEAL, alpha=0.55, edgecolor="white")
    for q, c, lab in [(mc["p10"], SLATE, "P10"), (mc["p50"], NAVY, "P50 (median)"),
                      (mc["p90"], SLATE, "P90")]:
        ax.axvline(q, color=c, lw=1.6, ls="--")
        ax.text(q, ax.get_ylim()[1] * 0.92, f" {lab} ${q:,.0f}", color=c,
                fontsize=9, rotation=90, va="top")
    if price:
        ax.axvline(price, color=RED, lw=2)
        ax.text(price, ax.get_ylim()[1] * 0.55, f" price ${price:,.0f}",
                color=RED, fontsize=9.5, fontweight="bold", rotation=90, va="top")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_xlabel("Intrinsic value per share")
    ax.set_ylabel("Simulations")
    ax.set_title(f"{ticker} — Monte Carlo valuation ({len(mc['values']):,} runs)",
                 fontsize=13, fontweight="bold", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8)
    return _save(fig, f"03_monte_carlo_{ticker}.png")


def tornado_chart(ticker, tor):
    base = tor["base"]
    d = tor["drivers"][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for i, row in enumerate(d):
        lo, hi = row["low"], row["high"]
        ax.barh(i, hi - base, left=base, color=GREEN, alpha=0.8, edgecolor="white")
        ax.barh(i, lo - base, left=base, color=RED, alpha=0.8, edgecolor="white")
    ax.axvline(base, color=NAVY, lw=1.5)
    ax.text(base, len(d) - 0.3, f" base ${base:,.0f}", color=NAVY, fontsize=9)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([r["driver"] for r in d])
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_title(f"{ticker} — what moves the valuation", fontsize=13,
                 fontweight="bold", loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, f"04_tornado_{ticker}.png")
