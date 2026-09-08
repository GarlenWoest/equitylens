"""Write the DCF model to a formatted .xlsx so it can be opened and audited in
Excel like a normal analyst model.

    python src/export_excel.py AAPL
"""
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from run_valuation import value

NAVY = "14233A"
GOLD = "C08A2D"
LIGHT = "EEF1F4"


def _hdr(ws, cell, text):
    ws[cell] = text
    ws[cell].font = Font(bold=True, color="FFFFFF")
    ws[cell].fill = PatternFill("solid", fgColor=NAVY)
    ws[cell].alignment = Alignment(horizontal="left")


def _money(ws, cell, val, pct=False):
    ws[cell] = val
    ws[cell].number_format = "0.0%" if pct else "#,##0"


def build_workbook(ticker):
    r = value(ticker)
    d = r["dcf"]
    wb = Workbook()
    ws = wb.active
    ws.title = "DCF"
    ws.column_dimensions["A"].width = 30
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 14

    ws["A1"] = f"{d['company']} ({ticker.upper()}) — DCF valuation"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)

    # Assumptions
    _hdr(ws, "A3", "Assumptions")
    rows = [("WACC", d["wacc"], True), ("Cost of equity", d["cost_of_equity"], True),
            ("Terminal growth", d["terminal_growth"], True),
            ("EBIT margin", d["drivers"]["ebit_margin"], True),
            ("Effective tax", d["drivers"]["tax_rate"], True),
            ("Capex % rev", d["drivers"]["capex_pct"], True)]
    for i, (label, val, pct) in enumerate(rows, start=4):
        ws[f"A{i}"] = label
        _money(ws, f"B{i}", val, pct)

    # Projected FCF
    start = 4 + len(rows) + 1
    _hdr(ws, f"A{start}", "Projected free cash flow ($, millions)")
    heads = ["Year", "Revenue", "EBIT", "NOPAT", "D&A", "Capex", "FCF"]
    for j, h in enumerate(heads):
        c = ws.cell(row=start + 1, column=1 + j, value=h)
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor=LIGHT)
    for k, s in enumerate(d["schedule"]):
        row = start + 2 + k
        ws.cell(row=row, column=1, value=f"Y{s['year']}")
        for j, key in enumerate(["revenue", "ebit", "nopat", "da", "capex", "fcf"]):
            c = ws.cell(row=row, column=2 + j, value=round(s[key] / 1e6))
            c.number_format = "#,##0"

    # Valuation bridge
    b = start + 2 + len(d["schedule"]) + 1
    _hdr(ws, f"A{b}", "Valuation bridge ($, millions)")
    bridge = [("PV of explicit FCF", d["pv_fcf"]),
              ("PV of terminal value", d["pv_terminal"]),
              ("Enterprise value", d["enterprise_value"]),
              ("Less: net debt", -d["net_debt"]),
              ("Equity value", d["equity_value"])]
    for i, (label, val) in enumerate(bridge, start=b + 1):
        ws[f"A{i}"] = label
        ws.cell(row=i, column=2, value=round(val / 1e6)).number_format = "#,##0"
    last = b + 1 + len(bridge)
    ws[f"A{last}"] = "Value per share"
    ws.cell(row=last, column=2, value=round(d["value_per_share"], 2)).number_format = "$#,##0.00"
    ws[f"A{last}"].font = Font(bold=True, color=GOLD)
    ws[f"A{last+1}"] = "Current price"
    ws.cell(row=last + 1, column=2, value=d["market_price"]).number_format = "$#,##0.00"

    out = f"examples/{ticker.upper()}_model.xlsx"
    wb.save(out)
    return out


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print("wrote", build_workbook(t))
