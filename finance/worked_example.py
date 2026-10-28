"""IS-Retail finance worked example – company code US10, DC01 and store ST01 (USD, whole dollars).

Every journal line must use an account from chart_of_accounts.csv. The script checks that each
entry balances, that the trial balance balances, that the balance sheet balances, that all
clearing accounts are zero and that the inventory value equals units on hand x moving average cost.

Run:  python finance/worked_example.py           (prints results, writes finance/output/*.csv)
      python finance/worked_example.py --check   (exit code 1 on any failed check; used by CI)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COA = {r["account"]: r for r in csv.DictReader(open(HERE / "chart_of_accounts.csv", encoding="utf-8"))}

# ---- Scenario parameters -------------------------------------------------------------
QTY_PO, COST, STO = 1000, 8, 600            # units bought into DC01 @ cost; units moved DC01 -> ST01
REG, PROMO = 20, 15                          # regular and promotion (PR-FALL) prices
SOLD_REG, SOLD_PROMO, RET, SHRINK = 300, 200, 10, 5
TAXR, REBATE, CARD_FEE, CIT = 0.08, 0.03, 0.025, 0.25
CARD_SHARE = 2 / 3                           # share of tenders paid by card
PAYROLL, RENT, OPENING = 1500, 1200, 100000

po = QTY_PO * COST
rebate = round(po * REBATE)
sto = STO * COST
rev = SOLD_REG * REG + SOLD_PROMO * PROMO
tax = round(rev * TAXR)
gross = rev + tax
card = round(gross * CARD_SHARE)
cash = gross - card
ret_rev, ret_cost = RET * REG, RET * COST
ret_tax = round(ret_rev * TAXR)
cogs = (SOLD_REG + SOLD_PROMO) * COST
fee = round(card * CARD_FEE)
shrink = SHRINK * COST
deposit = cash - ret_rev - ret_tax

# ---- Journal entries: (id, phase, transaction, doc type, text, [(account, debit, credit, assignment)]) ----
J = [
    ("0", "Opening", "Migration Cockpit – G/L balances", "SA", "Opening capital", [("11001000", OPENING, 0, ""), ("31000000", 0, OPENING, "")]),
    ("R1", "Buy", "WRP1R / ME21N", "—", f"Replenishment proposal and PO: {QTY_PO} x TS-100 (variants S/M/L) @ {COST} for DC01 – no posting", []),
    ("R2", "Buy", "MIGO 101 / EWM inbound", "WE", "Goods receipt at DC01 (moving average price)", [("13400000", po, 0, "BSX · site DC01 · PC 1100"), ("21200000", 0, po, "WRX")]),
    ("R3", "Buy", "MIRO", "RE", "Vendor invoice", [("21200000", po, 0, "WRX"), ("21100000", 0, po, "Vendor 1000700")]),
    ("R4", "Buy", "Condition contract accrual", "SA", f"Vendor rebate accrual {REBATE:.0%} of invoiced value", [("12600100", rebate, 0, "Condition contract CC-0001"), ("52500000", 0, rebate, "COGS reduction")]),
    ("R5", "Buy", "F110", "ZP", "Vendor payment", [("21100000", po, 0, ""), ("11001000", 0, po, "")]),
    ("D1", "Move", "STO · VL10B · VL02N (mvt 641)", "WL", f"Stock transport DC01 -> ST01: {STO} units", [("13400000", sto, 0, "Site ST01 · PC 2101"), ("13400000", 0, sto, "Site DC01 · PC 1100")]),
    ("D2", "Move", "Store GR (Fiori, mvt 101)", "—", "Goods receipt in store from stock in transit – value already moved at goods issue", []),
    ("S1", "Sell", "POS inbound WPUUMS (mvt 251)", "WA", f"ST01 daily sales: {SOLD_REG} @ {REG} + {SOLD_PROMO} @ {PROMO} (PR-FALL)", [("50000000", cogs, 0, "GBB-VAX · ST01"), ("13400000", 0, cogs, "BSX · ST01")]),
    ("S2", "Sell", "POS inbound WPUUMS / WPUTAB", "RV", "Revenue, sales tax and tenders", [("11009400", cash, 0, "Tender: cash"), ("11009500", card, 0, "Tender: card"), ("41000000", 0, rev, "VKOA ERL · ST01"), ("22000000", 0, tax, "MWS")]),
    ("S3", "Sell", "POS inbound return (mvt 252)", "RV", f"Customer returns {RET} units @ {REG}", [("41100000", ret_rev, 0, "Sales returns"), ("22000000", ret_tax, 0, ""), ("11009400", 0, ret_rev + ret_tax, "Cash refund"), ("13400000", ret_cost, 0, "Mvt 252 · ST01"), ("50000000", 0, ret_cost, "")]),
    ("S4", "Sell", "FEBAN – store deposit", "ZB", "Store cash deposited at bank", [("11001000", deposit, 0, ""), ("11009400", 0, deposit, "")]),
    ("S5", "Sell", "FEBAN – acquirer settlement", "ZB", f"Card settlement net of {CARD_FEE:.1%} fee", [("11001000", card - fee, 0, ""), ("63600000", fee, 0, "CC store ST01"), ("11009500", 0, card, "")]),
    ("S6", "Count", "Store physical inventory (mvt 702)", "WI", f"Shrinkage {SHRINK} units", [("52300000", shrink, 0, "GBB-INV · ST01"), ("13400000", 0, shrink, "ST01")]),
    ("O1", "Operate", "Payroll posting", "Y2", "Store payroll", [("61000000", PAYROLL, 0, "CC store ST01"), ("21400000", 0, PAYROLL, "")]),
    ("O2", "Operate", "Bank transfer", "ZP", "Net pay", [("21400000", PAYROLL, 0, ""), ("11001000", 0, PAYROLL, "")]),
    ("O3", "Operate", "FB60", "KR", "Store rent invoice (open)", [("62000000", RENT, 0, "CC store ST01"), ("21150000", 0, RENT, "Landlord 1000800")]),
]

def pnl(acct: str) -> bool:
    return COA[acct]["fsv_node"][0] in "4567"

pre = sum(c - d for e in J for (a, d, c, _) in e[5] if pnl(a))
itax = round(pre * CIT)
J.append(("C1", "Close", "FB50", "SA", f"Income tax provision {CIT:.0%}", [("79000000", itax, 0, f"25% x {pre:,}"), ("22200000", 0, itax, "")]))
ni = pre - itax

def run_checks() -> list[str]:
    errors = []
    for e in J:
        for a, *_ in e[5]:
            if a not in COA:
                errors.append(f"{e[0]}: account {a} not in chart of accounts")
        d, c = sum(l[1] for l in e[5]), sum(l[2] for l in e[5])
        if d != c:
            errors.append(f"{e[0]}: debit {d} != credit {c}")
    return errors

errors = run_checks()
tb: dict[str, int] = {}
for e in J:
    for a, d, c, _ in e[5]:
        tb[a] = tb.get(a, 0) + d - c

def node(prefix: str) -> int:
    return sum(v for a, v in tb.items() if COA[a]["fsv_node"].startswith(prefix))

tot_d, tot_c = sum(v for v in tb.values() if v > 0), -sum(v for v in tb.values() if v < 0)
assets, liab, equity = node("1"), -node("2"), -node("3") + ni
dc_units, st_units = QTY_PO - STO, STO - SOLD_REG - SOLD_PROMO + RET - SHRINK
net_rev, net_cogs = rev - ret_rev, cogs - ret_cost
gm = net_rev - net_cogs + rebate - shrink
checks = {
    "trial balance balances": tot_d == tot_c,
    "balance sheet balances": assets == liab + equity,
    "GR/IR, cash-in-transit and card clearing are zero": all(tb.get(a, 0) == 0 for a in ("21200000", "11009400", "11009500")),
    "inventory = units x moving average cost": (dc_units + st_units) * COST == tb["13400000"],
    "profit before tax = gross margin - opex": pre == gm - PAYROLL - RENT - fee,
}
errors += [f"check failed: {k}" for k, ok in checks.items() if not ok]

RESULTS = dict(po=po, rebate=rebate, sto=sto, rev=rev, tax=tax, gross=gross, card=card, cash=cash, ret_rev=ret_rev, ret_tax=ret_tax, ret_cost=ret_cost,
               cogs=cogs, fee=fee, shrink=shrink, pre=pre, itax=itax, ni=ni, assets=assets, liab=liab, equity=equity, dc_units=dc_units, st_units=st_units,
               net_rev=net_rev, net_cogs=net_cogs, gm=gm, inventory=tb["13400000"], tot_d=tot_d, tot_c=tot_c, payroll=PAYROLL, rent=RENT, opening=OPENING)

def write_outputs(out: Path = HERE / "output") -> None:
    out.mkdir(exist_ok=True)
    with open(out / "journal_entries.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["entry", "phase", "transaction", "doc_type", "text", "account", "account_name", "debit", "credit", "assignment"])
        for e in J:
            if not e[5]:
                w.writerow([e[0], e[1], e[2], e[3], e[4], "", "", "", "", ""])
            for a, d, c, n in e[5]:
                w.writerow([e[0], e[1], e[2], e[3], e[4], a, COA[a]["description"], d or "", c or "", n])
    with open(out / "trial_balance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["account", "description", "fsv_node", "debit", "credit"])
        for a in sorted(tb):
            if tb[a]:
                w.writerow([a, COA[a]["description"], COA[a]["fsv_node"], max(tb[a], 0) or "", max(-tb[a], 0) or ""])
        w.writerow(["", "Total", "", tot_d, tot_c])

if __name__ == "__main__":
    write_outputs()
    for k, v in RESULTS.items():
        print(f"{k:>10}: {v:,}")
    for k, ok in checks.items():
        print(("PASS " if ok else "FAIL ") + k)
    if errors:
        print("\n".join(errors))
    if "--check" in sys.argv and errors:
        sys.exit(1)
