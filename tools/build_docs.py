"""Generate docs/05-chart-of-accounts.md and docs/08-finance-worked-example.md from the finance sources,
so the documentation always matches finance/chart_of_accounts.csv and finance/worked_example.py.
Run: python tools/build_docs.py
"""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("we", ROOT / "finance" / "worked_example.py")
we = importlib.util.module_from_spec(spec); spec.loader.exec_module(we)
R = we.RESULTS
coa = list(csv.DictReader(open(ROOT / "finance" / "chart_of_accounts.csv", encoding="utf-8")))
ad = list(csv.DictReader(open(ROOT / "finance" / "account_determination.csv", encoding="utf-8")))


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def money(n, bold=False):
    s = f"({abs(n):,.2f})" if n < 0 else f"{n:,.2f}"
    return f"**{s}**" if bold else s


NAV = "[← Contents](../README.md#contents)"

# ------------------------------------------------------------------ Chapter 05
classes = [("1", "Assets"), ("2", "Liabilities"), ("3", "Equity and migration clearing"), ("4", "Revenue and sales deductions"),
           ("5", "Cost of goods sold"), ("6", "Operating expenses"), ("7", "Financial result"), ("8", "Income taxes"), ("9", "Secondary cost elements (CO)")]
groups = {}
for r in coa:
    groups.setdefault(r["account_group"], []).append(r["account"])
ch5 = [f"# 5. Chart of Accounts\n\n{NAV}\n",
       "Company code **US10** uses one operational chart of accounts based on the SAP Best Practices chart **YCOA** (8-digit accounts), "
       "extended with retail-specific accounts: POS tender clearing (cash, card, gift card, online payment provider), vendor rebate receivables "
       "and income from condition contracts, gift-card and store-credit liabilities, refund liability for expected returns, POS discounts, "
       "shrinkage, vendor markdown funding, store occupancy and card fees, and a **data migration clearing account (39990000)** that must be "
       "zero after the initial stock and G/L balance loads. The machine-readable source is "
       "[`finance/chart_of_accounts.csv`](../finance/chart_of_accounts.csv) (" + str(len(coa)) + " accounts).\n",
       "![Chart of accounts structure](../diagrams/coa_structure.png)\n",
       "## 5.1 Design principles\n",
       "- **YCOA as the base**, so SAP Best Practices content (account determination, financial statement version, reports) works with minimal change; "
       "retail accounts are added in free number ranges. Account numbers in this document are the client's design – verify them against the YCOA delivered in your release before build [VERIFY].\n"
       "- **Inventory at moving average cost per site**; one inventory account (13400000) for all merchandise, split by site and profit center through the material ledger and document splitting.\n"
       "- **Every POS tender has its own clearing account** that must be zero once the bank deposit or acquirer settlement is matched – the daily control for 50 stores.\n"
       "- **Vendor rebates and vendor-funded markdowns reduce cost of goods sold** (52500000, 52600000), not revenue.\n"
       "- **Returns and discounts are revenue deductions** (41100000–41300000) so gross and net sales can be reported by store.\n"
       "- **Profit center per store and DC** (2101–2150, 1100) with document splitting gives a store P&L and balance sheet.\n"
       "- **Migration clearing 39990000**: initial stock (movement 561) and G/L balances are both posted against it; it must net to zero (reconciled automatically by the ETL).\n",
       "## 5.2 Account groups\n",
       table(["Group", "Content", "Number of accounts"], [(g, {"CASH": "Cash, bank and POS tender clearing", "RECV": "Receivables, vendor rebates, prepaid, tax", "INV": "Merchandise inventory",
             "FIXA": "Fixed assets, right-of-use, intangibles, deferred tax", "PAYB": "Payables, GR/IR, accruals, gift cards, refund liability, taxes", "DEBT": "Leases and borrowings",
             "EQTY": "Equity", "MIGR": "Data migration clearing", "REVN": "Revenue and sales deductions", "COGS": "Cost of goods sold, shrinkage, rebates", "PERS": "Personnel",
             "OCCU": "Store occupancy", "SGA": "Selling, general and administrative", "DEPR": "Depreciation and amortisation", "FIN": "Financial result", "TAX": "Income taxes",
             "SECC": "Secondary cost elements (CO only)"}.get(g, g), len(v)) for g, v in groups.items()]) + "\n"]
for i, (d, title) in enumerate(classes, start=3):
    rows = [(r["account"], r["description"], r["fsv_node"], r["fsv_line"], r["account_determination"], r["co_category"]) for r in coa if r["account"][0] == d]
    if rows:
        ch5.append(f"## 5.{i} {title} ({d}xxxxxxx)\n")
        ch5.append(table(["Account", "Description", "FSV node", "Statement line", "Account determination", "CO"], rows) + "\n")
ch5 += ["## 5.12 Automatic account determination\n",
        table(["Area", "Key", "Business event", "Debit", "Credit"], [(r["area"], r["key"], r["business_event"], r["debit"], r["credit"]) for r in ad]) + "\n",
        "## 5.13 Financial statement version (FSV US10)\n",
        table(["Node", "Line"], sorted({(r["fsv_node"], r["fsv_line"]) for r in coa if r["fsv_node"] != "9.0"})) + "\n",
        "Configuration of the chart (OB13, OB62, OBD4, FS00, OB53, OBYC, VKOA, AO90, OB58, document splitting) is in [Chapter 6](06-configuration.md#69-chart-of-accounts-and-finance-integration).\n"]
(ROOT / "docs" / "05-chart-of-accounts.md").write_text("\n".join(ch5), encoding="utf-8")

# ------------------------------------------------------------------ Chapter 08
je = []
for e in we.J:
    if not e[5]:
        je.append((e[0], e[2], "—", "—", e[4], "", "", ""))
    for i, (a, d, c, n) in enumerate(e[5]):
        je.append(("" if i else e[0], "" if i else e[2], "" if i else e[3], a, we.COA[a]["description"], f"{d:,.2f}" if d else "", f"{c:,.2f}" if c else "", n))
tb = [(a, we.COA[a]["description"], we.COA[a]["fsv_node"], f"{v:,.2f}" if v > 0 else "", f"{-v:,.2f}" if v < 0 else "") for a, v in sorted(we.tb.items()) if v]
tbv = we.tb
ch8 = f"""# 8. Finance Integration and Worked Example

{NAV}

This chapter follows one article from purchase to the financial statements. Every amount below is produced and
checked by [`finance/worked_example.py`](../finance/worked_example.py) (run in CI): each entry balances, the trial balance
balances, the balance sheet balances, all clearing accounts are zero and inventory equals units on hand × moving average cost.
All accounts come from the chart of accounts in [Chapter 5](05-chart-of-accounts.md).

## 8.1 Retail events and their postings

{table(["Event", "Movement / document", "Debit", "Credit"], [
    ("Vendor goods receipt at DC", "101 / WE", "13400000 Inventory (DC01)", "21200000 GR/IR"), ("Vendor invoice", "MIRO / RE", "21200000 GR/IR", "21100000 Vendor"),
    ("Rebate accrual", "Condition contract", "12600100 Rebate receivable", "52500000 Rebate income"), ("Stock transfer DC → store", "641 / 101", "13400000 (ST01, PC 2101)", "13400000 (DC01, PC 1100)"),
    ("POS sale – stock", "251", "50000000 COGS", "13400000 Inventory (store)"), ("POS sale – revenue & tenders", "POS inbound", "11009400 cash, 11009500 card", "41000000 revenue, 22000000 tax"),
    ("POS return", "252", "41100000 returns, 22000000 tax, 13400000", "11009400 cash, 50000000 COGS"), ("Cash deposit / card settlement", "FEBAN", "11001000 bank, 63600000 card fees", "11009400 / 11009500"),
    ("Inventory difference", "701 / 702", "52300000 Shrinkage", "13400000 Inventory"), ("Initial stock at migration", "561", "13400000 Inventory", "39990000 Migration clearing")])}

## 8.2 Scenario

Company code US10 starts with USD {R['opening']:,} of capital. It buys {we.QTY_PO:,} Basic Tees (generic article TS-100, variants S/M/L) at
USD {we.COST} into DC01, moves {we.STO} to store ST01, sells {we.SOLD_REG} at the regular price of USD {we.REG} and {we.SOLD_PROMO} at the promotion
price of USD {we.PROMO} (promotion PR-FALL), accepts {we.RET} returns, counts {we.SHRINK} units of shrinkage, accrues a 3% vendor rebate
and pays store payroll and rent. Sales tax is 8%; two thirds of tenders are card (2.5% acquirer fee).

```mermaid
flowchart LR
  V[Vendor] -- "PO 1,000 @ 8" --> DC[DC01 · EWM]
  DC -- "STO 600" --> ST[Store ST01]
  ST -- "POS: 300 @ 20 + 200 @ 15" --> C[Customers]
  C -- "10 returns" --> ST
  ST -- "count: 5 short" --> X[Shrinkage]
  ST -- "TLOG" --> CAR[CAR sales audit] --> FI[S/4HANA FI / CO]
```

## 8.3 Journal entries

{table(["Step", "Transaction", "Doc", "G/L", "Account", "Debit", "Credit", "Assignment"], je)}
| | | | | **Total** | **{R['tot_d']:,.2f}** | **{R['tot_c']:,.2f}** | |

## 8.4 Inventory roll-forward

{table(["Movement", "DC01 units", "ST01 units", "Value (USD)"], [("Vendor GR", we.QTY_PO, "", money(R['po'])), ("STO DC01 → ST01", f"−{we.STO}", f"+{we.STO}", "0.00 (site transfer)"),
    ("POS sales", "", f"−{we.SOLD_REG + we.SOLD_PROMO}", money(-R['cogs'])), ("POS returns", "", f"+{we.RET}", money(R['ret_cost'])), ("Shrinkage", "", f"−{we.SHRINK}", money(-R['shrink'])),
    ("**Closing**", f"**{R['dc_units']}**", f"**{R['st_units']}**", money(R['inventory'], True))])}

## 8.5 Trial balance

{table(["G/L account", "Description", "FSV", "Debit", "Credit"], tb + [("", "**Total**", "", f"**{R['tot_d']:,.2f}**", f"**{R['tot_c']:,.2f}**")])}

## 8.6 Income statement (store ST01 = company in this example)

{table(["Line", "USD"], [("Gross sales (41000000)", money(R['rev'])), ("Returns (41100000)", money(-R['ret_rev'])), ("**Net sales**", money(R['net_rev'], True)),
    ("Cost of goods sold at moving average cost (50000000)", money(-R['net_cogs'])), ("Vendor rebate income (52500000)", money(R['rebate'])), ("Shrinkage (52300000)", money(-R['shrink'])),
    ("**Gross margin**", money(R['gm'], True)), ("Store payroll (61000000)", money(-R['payroll'])), ("Store rent (62000000)", money(-R['rent'])), ("Card fees (63600000)", money(-R['fee'])),
    ("**Profit before tax**", money(R['pre'], True)), ("Income tax 25% (79000000)", money(-R['itax'])), ("**Net income**", money(R['ni'], True))])}

## 8.7 Balance sheet

{table(["Line", "USD"], [("Cash and bank (11001000)", money(tbv['11001000'])), ("Vendor rebate receivable (12600100)", money(tbv['12600100'])),
    (f"Inventory – DC01 {R['dc_units']} + ST01 {R['st_units']} units × 8 (13400000)", money(tbv['13400000'])), ("**Total assets**", money(R['assets'], True)),
    ("Payables – landlord (21150000)", money(-tbv['21150000'])), ("Sales tax payable (22000000)", money(-tbv['22000000'])), ("Income tax payable (22200000)", money(-tbv['22200000'])),
    ("**Total liabilities**", money(R['liab'], True)), ("Share capital (31000000)", money(-tbv['31000000'])), ("Net income for the period", money(R['ni'])),
    ("**Total equity**", money(R['equity'], True)), ("**Total liabilities and equity**", money(R['liab'] + R['equity'], True))])}

> **Checks (automated):** assets {R['assets']:,.2f} = liabilities {R['liab']:,.2f} + equity {R['equity']:,.2f}. GR/IR (21200000), store cash in transit
> (11009400) and card clearing (11009500) are zero because every receipt, deposit and settlement has been matched – the target daily state for every store.

## 8.8 Store KPIs from the example

{table(["KPI", "Value"], [("Net sales ST01", money(R['net_rev'])), ("Gross margin %", f"{R['gm'] / R['net_rev']:.1%}"), ("Promotion share of units", f"{we.SOLD_PROMO / (we.SOLD_REG + we.SOLD_PROMO):.0%}"),
    ("Shrinkage % of net sales", f"{R['shrink'] / R['net_rev']:.2%}"), ("Return rate (units)", f"{we.RET / (we.SOLD_REG + we.SOLD_PROMO):.1%}"), ("Sell-through ST01", f"{(we.SOLD_REG + we.SOLD_PROMO - we.RET) / we.STO:.0%}")])}

## 8.9 Daily finance controls in production

{table(["Control", "Account / report", "Target"], [("POS cash takings deposited", "11009400 Store cash in transit by store", "0 after bank statement"),
    ("Card settlements received", "11009500 Payment card clearing", "0 after acquirer file"), ("Goods received = invoiced", "21200000 GR/IR", "Ageing < 30 days"),
    ("Rebates accrued", "12600100 vs condition contract", "Accrual = contract rate × invoiced value"), ("Store stock accuracy", "52300000 Shrinkage by store and MC", "< 1.5% of sales"),
    ("Migration clearing", "39990000", "0 from go-live onwards")])}
"""
(ROOT / "docs" / "08-finance-worked-example.md").write_text(ch8, encoding="utf-8")
print("docs 05 and 08 generated")
