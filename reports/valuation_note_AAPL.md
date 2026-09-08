# Valuation note — Apple (AAPL)

*Based on FY2025 10-K figures pulled from SEC EDGAR. Market inputs are snapshots
as of 2026-09-01 — see data/assumptions.json.*

## Bottom line

On a conservative, history-based DCF, Apple is worth roughly **$100–125 per
share** (base case $104; Monte Carlo P10–P90 $89–$123). Trading comps stretch that
to **$132–$164**. Both sit below the **~$245** market price. I'd frame Apple as
**priced for more than the fundamentals alone support** — not an automatic short,
but a stock where you're paying up for quality and durability the model won't give
you for free.

## How I got there

- **Cash flows:** FY2025 revenue $416B, ~31% EBIT margin, low capex (~3% of
  revenue) and roughly neutral working capital, so Apple converts a lot of EBIT
  into free cash. Projected FCF runs ~$110–125B over five years.
- **Discount rate:** CAPM cost of equity of ~9.6% (beta 1.2, 4.2% risk-free, 4.5%
  ERP); WACC ~9.5% given a mostly-equity capital structure.
- **Terminal:** 2.5% perpetuity growth. ~72% of value sits in the terminal — high,
  which is why the sensitivity and Monte Carlo work matters.

## The number that matters

A reverse DCF says the current price implies a discount rate of about **5.5%**.
That's the real debate: is Apple's business ~4 points less risky than my CAPM
assumption, or is the market optimistic? Everything else is detail.

## What would change my mind

- A credibly higher terminal growth (services mix, installed-base monetization)
  moves the base case up quickly — see the sensitivity grid (`assets/02_sensitivity_AAPL.png`).
- A lower beta / risk-free environment narrows the gap to price.
- Buybacks keep shrinking the share count (~15.0B diluted, down from 16.3B in
  FY2022), which lifts per-share value independent of the business.

## Caveats

Comps for Apple are imperfect (few true peers). Market inputs are snapshots, not a
live feed. Not investment advice.
