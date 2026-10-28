"""Silver (cleansed legacy) -> gold (SAP Migration Cockpit staging layout) transformations.

Each function takes pandas DataFrames with the legacy columns described in etl/README.md and the
mapping rules, and returns (gold, dq) where gold uses SAP technical field names and dq holds the
data-quality findings (see quality.DQ_COLUMNS). Rows with ERROR findings are excluded from gold.
"""
from __future__ import annotations

import pandas as pd

from .quality import finding, frame, is_valid_gtin
from .rules import profit_center

MIGRATION_CLEARING = "39990000"   # offset account for initial stock (mvt 561) and G/L balance loads
INVENTORY_ACCOUNT = "13400000"


def _clean(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().replace({"nan": "", "None": ""})


# ---------------------------------------------------------------------------------------------
def sites(stores: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    dq, out = [], []
    for r in stores.itertuples(index=False):
        sid = str(r.store_id).strip().upper()
        stype = str(r.store_type).strip().upper()
        if stype not in rules["site_type"]:
            dq.append(finding("site", sid, "SITE_TYPE_UNMAPPED", "ERROR", f"store_type '{stype}' has no site category"))
            continue
        try:
            pc = profit_center(sid, rules)
        except KeyError as e:
            dq.append(finding("site", sid, "PROFIT_CENTER_UNMAPPED", "ERROR", str(e)))
            continue
        cat = rules["site_type"][stype]
        out.append({
            "WERKS": sid, "NAME1": str(r.store_name).strip()[:30], "VLFKZ": cat["vlfkz"], "PROFILE": cat["profile"],
            "BUKRS": rules["company_code"], "VKORG": rules["sales_org"],
            "VTWEG": rules["distribution_channel_online"] if stype == "WEB" else rules["distribution_channel_store"],
            "PRCTR": pc, "STRAS": str(r.street).strip(), "ORT01": str(r.city).strip(), "REGIO": str(r.state).strip(),
            "PSTLZ": str(r.zip).strip().zfill(5), "LAND1": str(r.country).strip(), "EROED": str(r.open_date)})
    gold = pd.DataFrame(out)
    if not gold.empty and gold["WERKS"].duplicated().any():
        for k in gold.loc[gold["WERKS"].duplicated(), "WERKS"]:
            dq.append(finding("site", k, "DUPLICATE_SITE", "ERROR", "site id appears more than once"))
        gold = gold.drop_duplicates("WERKS", keep=False)
    return gold, frame(dq)


# ---------------------------------------------------------------------------------------------
def suppliers(vendors: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    dq, out = [], []
    recon = rules["vendor_recon_account"]
    dup_tax = vendors["tax_id"].astype(str).duplicated(keep=False) & vendors["tax_id"].notna()
    for i, r in enumerate(vendors.itertuples(index=False)):
        vid = str(r.vendor_id).strip()
        if dup_tax.iloc[i]:
            dq.append(finding("supplier", vid, "DUPLICATE_TAX_ID", "ERROR", f"tax id {r.tax_id} used by more than one vendor – merge before load"))
            continue
        routing, account = str(r.bank_routing).strip(), str(r.bank_account).strip()
        if routing in ("", "nan") or account in ("", "nan"):
            dq.append(finding("supplier", vid, "MISSING_BANK", "WARNING", "no bank details – payment block set until four-eyes bank verification"))
            routing = account = ""
        country = str(r.country).strip()
        out.append({
            "PARTNER": vid, "BU_GROUP": rules["vendor_bp_grouping"], "NAME_ORG1": str(r.name).strip()[:40], "STREET": str(r.street).strip(),
            "CITY1": str(r.city).strip(), "REGION": str(r.state).strip(), "POST_CODE1": str(r.zip).strip(), "COUNTRY": country,
            "TAXNUM": str(r.tax_id).strip(), "BANKS": country if routing else "", "BANKL": routing, "BANKN": account,
            "BUKRS": rules["company_code"], "AKONT": recon.get(country, recon["default"]),
            "ZTERM": str(r.payment_terms).strip() if str(r.payment_terms) not in ("", "nan") else rules["payment_terms_default"],
            "EKORG": rules["purchasing_org"], "WAERS": rules["currency"], "ZAHLS": "" if routing else "A"})
    return pd.DataFrame(out), frame(dq)


# ---------------------------------------------------------------------------------------------
def variant_id(style: str, color: str, size: str) -> str:
    return f"{style}-{color}-{size}".upper().replace(" ", "")


def articles(items: pd.DataFrame, rules: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generic article per style (ATTYP 01) and one variant per colour/size (ATTYP 02) with its UPC."""
    dq, out = [], []
    df = items.copy()
    df["upc"] = _clean(df["upc"]).str.replace(r"\.0$", "", regex=True)
    df["mc_key"] = df["dept"].astype(str) + "-" + df["class"].astype(str)
    df["variant"] = [variant_id(s, c, z) for s, c, z in zip(df["style"], df["color"], df["size"])]
    dup_upc = df["upc"].ne("") & df["upc"].duplicated(keep=False)
    bad = set()
    for i, r in df.iterrows():
        if not is_valid_gtin(r["upc"]):
            dq.append(finding("article", r["variant"], "INVALID_GTIN", "ERROR", f"UPC '{r['upc']}' fails GS1 check digit / length"))
            bad.add(i)
        elif dup_upc.loc[i]:
            dq.append(finding("article", r["variant"], "DUPLICATE_GTIN", "ERROR", f"UPC {r['upc']} assigned to more than one variant"))
            bad.add(i)
        if r["mc_key"] not in rules["merchandise_category"]:
            dq.append(finding("article", r["variant"], "MC_UNMAPPED", "ERROR", f"dept/class {r['mc_key']} has no merchandise category"))
            bad.add(i)
    good = df.drop(index=list(bad))
    for style, g in good.groupby("style", sort=True):
        mc = rules["merchandise_category"][g["mc_key"].iloc[0]]
        desc = str(g["style_desc"].iloc[0]).strip()[:40]
        vendor = str(g["vendor_id"].iloc[0]).strip()
        out.append({"MATNR": str(style).upper(), "ATTYP": "01", "SATNR": "", "MTART": rules["article_type"], "MATKL": mc, "MAKTX": desc,
                    "MEINS": rules["base_uom"], "EAN11": "", "NUMTP": "", "COLOR": "", "SIZE": "", "LIFNR": vendor})
        for r in g.itertuples(index=False):
            out.append({"MATNR": r.variant, "ATTYP": "02", "SATNR": str(style).upper(), "MTART": rules["article_type"], "MATKL": mc,
                        "MAKTX": f"{desc} {r.color} {r.size}"[:40], "MEINS": rules["base_uom"], "EAN11": r.upc,
                        "NUMTP": "UC" if len(r.upc) == 12 else "HE", "COLOR": str(r.color).upper(), "SIZE": str(r.size).upper(), "LIFNR": vendor})
    return pd.DataFrame(out), frame(dq)


# ---------------------------------------------------------------------------------------------
def sales_prices(items: pd.DataFrame, article_gold: pd.DataFrame, rules: dict, valid_from: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retail price condition VKP0 per variant for the store distribution chain."""
    dq, out = [], []
    variants = set(article_gold.loc[article_gold["ATTYP"] == "02", "MATNR"])
    endings = tuple(rules["price_point_endings"])
    for r in items.itertuples(index=False):
        mat = variant_id(r.style, r.color, r.size)
        if mat not in variants:
            continue  # article rejected upstream; already reported in article DQ
        price, cost = float(r.retail_price), float(r.unit_cost)
        if price <= 0:
            dq.append(finding("sales_price", mat, "PRICE_NOT_POSITIVE", "ERROR", f"retail price {price}"))
            continue
        if not f"{price:.2f}".endswith(endings):
            dq.append(finding("sales_price", mat, "PRICE_POINT", "WARNING", f"{price:.2f} does not follow price-point endings {endings}"))
        if price < cost:
            dq.append(finding("sales_price", mat, "PRICE_BELOW_COST", "WARNING", f"price {price:.2f} below cost {cost:.2f}"))
        out.append({"KSCHL": "VKP0", "VKORG": rules["sales_org"], "VTWEG": rules["distribution_channel_store"], "MATNR": mat,
                    "KBETR": round(price, 2), "KONWA": rules["currency"], "KPEIN": 1, "KMEIN": rules["base_uom"],
                    "DATAB": valid_from, "DATBI": rules["valid_to"]})
    return pd.DataFrame(out), frame(dq)


# ---------------------------------------------------------------------------------------------
def inventory_balances(onhand: pd.DataFrame, article_gold: pd.DataFrame, site_gold: pd.DataFrame, rules: dict, posting_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Initial stock (movement type 561) per variant and site at moving average cost.

    Large volumes: in Databricks this runs per site partition with applyInPandas (see notebook 02)."""
    dq, out = [], []
    upc_to_mat = dict(zip(article_gold.loc[article_gold["ATTYP"] == "02", "EAN11"], article_gold.loc[article_gold["ATTYP"] == "02", "MATNR"]))
    valid_sites = set(site_gold["WERKS"])
    for r in onhand.itertuples(index=False):
        site, upc = str(r.store_id).strip().upper(), str(r.upc).strip().replace(".0", "")
        key = f"{site}/{upc}"
        qty, cost = float(r.qty_on_hand), float(r.unit_cost)
        if site not in valid_sites:
            dq.append(finding("inventory_balance", key, "SITE_UNKNOWN", "ERROR", "site not in site gold")); continue
        if upc not in upc_to_mat:
            dq.append(finding("inventory_balance", key, "ARTICLE_UNKNOWN", "ERROR", "UPC not in article gold (rejected or missing)")); continue
        if qty < 0:
            dq.append(finding("inventory_balance", key, "NEGATIVE_STOCK", "ERROR", f"quantity {qty} – correct by count before load")); continue
        if qty == 0:
            continue
        out.append({"MATNR": upc_to_mat[upc], "WERKS": site, "LGORT": "0001", "BWART": "561", "ERFMG": qty, "ERFME": rules["base_uom"],
                    "EXBWR": round(qty * cost, 2), "WAERS": rules["currency"], "BUDAT": posting_date})
    return pd.DataFrame(out), frame(dq)


# ---------------------------------------------------------------------------------------------
def gl_balances(tb: pd.DataFrame, rules: dict, posting_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Legacy trial balance -> S/4HANA G/L balances.

    Inventory is migrated by the inventory-balance object (561 against the migration clearing account),
    so the legacy inventory balance is re-pointed to MIGRATION_CLEARING here; after both loads the
    clearing account must be zero (checked in reconcile.cross_object_checks)."""
    dq, out = [], []
    amap = rules["gl_account"]
    for r in tb.itertuples(index=False):
        legacy = str(r.legacy_account).strip()
        if legacy not in amap:
            dq.append(finding("gl_balance", legacy, "GL_UNMAPPED", "ERROR", "legacy account has no S/4HANA mapping")); continue
        amt = round(float(r.debit or 0) - float(r.credit or 0), 2)
        if amt == 0:
            continue
        acct = amap[legacy]
        site = str(r.store_id).strip().upper() if str(r.store_id) not in ("", "nan") else ""
        out.append({"BUKRS": rules["company_code"], "HKONT": MIGRATION_CLEARING if acct == INVENTORY_ACCOUNT else acct, "LEGACY_HKONT": acct,
                    "PRCTR": profit_center(site, rules) if site else "", "SHKZG": "S" if amt > 0 else "H", "WRBTR": abs(amt),
                    "WAERS": rules["currency"], "BUDAT": posting_date})
    gold = pd.DataFrame(out)
    if not gold.empty:
        net = round((gold["WRBTR"] * gold["SHKZG"].map({"S": 1, "H": -1})).sum(), 2)
        if net != 0:
            dq.append(finding("gl_balance", "TOTAL", "TB_NOT_BALANCED", "ERROR", f"mapped balances do not net to zero (difference {net})"))
    return gold, frame(dq)
