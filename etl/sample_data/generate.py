"""Generate the fictitious legacy extract used for local runs and unit tests (deterministic).

It contains deliberate data-quality defects so the DQ rules can be demonstrated:
  * one UPC with a wrong check digit, one duplicated UPC, one dept/class without merchandise category
  * one vendor without bank details, two vendors sharing a tax id
  * one negative on-hand quantity
Run: python etl/sample_data/generate.py
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent / "legacy"


def check_digit(body: str) -> int:
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def upc(n: int) -> str:
    body = f"0123456{n:04d}"           # 11-digit body, company prefix 0123456
    return body + str(check_digit(body))


def write(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


stores = [["DC01", "Distribution Center Ontario", "DC", "4500 Logistics Way", "Ontario", "CA", "91761", "US", "2015-03-01"],
          ["WEB1", "Online Store", "WEB", "100 Main St", "Los Angeles", "CA", "90012", "US", "2019-01-15"]]
cities = [("Pasadena", "91101"), ("Santa Monica", "90401"), ("Irvine", "92618"), ("Burbank", "91502"), ("Long Beach", "90802")]
for i, (city, z) in enumerate(cities, start=1):
    stores.append([f"ST{i:02d}", f"Store {city}", "STORE", f"{100 + i} Retail Ave", city, "CA", z, "US", f"201{6 + i % 3}-0{i}-01"])
write("legacy_stores.csv", ["store_id", "store_name", "store_type", "street", "city", "state", "zip", "country", "open_date"], stores)

vendors = [["1000700", "Basic Apparel Co", "1 Garment Rd", "Los Angeles", "CA", "90021", "US", "95-1111111", "122000247", "000123456789", "0001"],
           ["1000710", "Denim Works Ltd", "22 Indigo St", "Dallas", "TX", "75201", "US", "75-2222222", "111000025", "000987654321", "0002"],
           ["1000720", "Shirt Makers Inc", "9 Collar Ave", "New York", "NY", "10001", "US", "13-3333333", "", "", "0001"],
           ["1000730", "Kitchen Pro GmbH", "Hauptstr. 5", "Munich", "BY", "80331", "DE", "DE444444444", "DEUTDEMM", "DE89370400440532013000", "0003"],
           ["1000731", "Kitchen Pro (dup)", "Hauptstr. 5", "Munich", "BY", "80331", "DE", "DE444444444", "DEUTDEMM", "DE89370400440532013000", "0003"]]
write("legacy_vendors.csv", ["vendor_id", "name", "street", "city", "state", "zip", "country", "tax_id", "bank_routing", "bank_account", "payment_terms"], vendors)

items, n = [], 1
styles = [("TS-100", "Basic Tee", "10", "100", ["BLK", "WHT"], ["S", "M", "L"], 8.00, 19.99, "1000700"),
          ("DN-200", "Slim Jeans", "10", "110", ["IND"], ["30", "32", "34"], 18.00, 49.99, "1000710"),
          ("SH-300", "Oxford Shirt", "10", "120", ["BLU"], ["M", "L"], 12.00, 34.95, "1000720"),
          ("CW-400", "Skillet 10in", "20", "200", ["STL"], ["OS"], 15.00, 39.99, "1000730"),
          ("AC-500", "Gift Wrap", "90", "900", ["RED"], ["OS"], 1.00, 4.99, "1000700")]          # dept 90-900 unmapped
for style, desc, dept, cls, colors, sizes, cost, price, vend in styles:
    for c in colors:
        for s in sizes:
            items.append([style, desc, dept, cls, c, s, upc(n), f"{cost:.2f}", f"{price:.2f}", vend]); n += 1
items[2][6] = items[2][6][:-1] + str((int(items[2][6][-1]) + 1) % 10)      # TS-100-BLK-L: wrong check digit
items[7][6] = items[6][6]                                                     # DN-200-IND-32 duplicates DN-200-IND-30
write("legacy_items.csv", ["style", "style_desc", "dept", "class", "color", "size", "upc", "unit_cost", "retail_price", "vendor_id"], items)

onhand = []
qty = {"DC01": 120, "ST01": 12, "ST02": 10, "ST03": 8, "ST04": 6, "ST05": 4}
for site, q in qty.items():
    for it in items:
        onhand.append([site, it[6], q, it[7]])
onhand.append(["ST03", items[0][6], -2, items[0][7]])                          # negative stock
write("legacy_onhand.csv", ["store_id", "upc", "qty_on_hand", "unit_cost"], onhand)

# Trial balance: legacy inventory = value of the on-hand stock that passes DQ (rejected articles are
# written off in legacy before cutover), retained earnings is the balancing figure.
rejected = {2, 6, 7} | {i for i, it in enumerate(items) if it[2] == "90"}
inventory = sum(q * float(it[7]) for q in qty.values() for i, it in enumerate(items) if i not in rejected)
tb = [["1000", "", 250000.00, 0], ["1010", "ST01", 500.00, 0], ["1010", "ST02", 500.00, 0], ["1300", "", 1200.00, 0], ["1400", "", inventory, 0],
      ["1500", "", 80000.00, 0], ["1510", "", 0, 20000.00], ["2000", "", 0, 45000.00], ["2100", "", 0, 6000.00], ["2200", "", 0, 3200.00],
      ["2300", "", 0, 1500.00], ["3000", "", 0, 100000.00]]
tb.append(["3100", "", 0, round(sum(r[2] - r[3] for r in tb), 2)])
write("legacy_trial_balance.csv", ["legacy_account", "store_id", "debit", "credit"],
      [[a, s, f"{d:.2f}" if d else "", f"{c:.2f}" if c else ""] for a, s, d, c in tb])
print(f"written to {OUT}")
