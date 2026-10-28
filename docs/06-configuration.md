# 6. Configuration

[← Contents](../README.md#contents)

Transaction codes and IMG paths are those of SAP S/4HANA Retail; confirm items marked [VERIFY] in your release before build.

## 6.1 Enterprise structure and sites

| Setting | Transaction / IMG | Value |
|---|---|---|
| Company code, controlling area | OX02 / OKKP | US10 / A000 (shared with finance template) |
| Sales organisation & distribution channels | OVX5 / OVXI | R100; 10 stores, 20 online |
| Purchasing organisation | OX08 | R100 |
| Site categories & profiles | SPRO → Logistics – General → Retailing → Site → Site Profiles `[VERIFY]` | Z_STORE (category A = store), Z_DC (category B = distribution center), Z_WEB |
| Number ranges for sites | SPRO → Site → Number Ranges `[VERIFY]` | External: DC01, ST01–ST99 |
| Site master | WB01 / WB02 | Plant data, customer data, supply source, calendar, profit center |
| Plant ↔ company code / sales org | OX18 / OVX6 | All sites → US10; stores → R100/10 |

## 6.2 Merchandise categories and articles

| Setting | Transaction / IMG | Value |
|---|---|---|
| Merchandise categories | WG21 / WG22 | 11010 Tops & Tees, 11020 Denim, 12010 Shirts, 21010 Cookware |
| Merchandise category hierarchy | SPRO → Merchandise Category → Hierarchy Levels; WMATGRP* `[VERIFY]` | Levels: division, department, MC |
| Characteristics & class type 026 | CT04 / CL02 | COLOR, SIZE variant-creating; assigned to MC 11010 |
| Article types | OMS2 / MM41 defaults | HAWA, NLAG; field selection per type |
| Article master | MM41 / MM42 / MM43 | Basic, listing, purchasing, sales, logistics DC/store, POS, accounting |
| EAN number ranges & checks | SPRO → Logistics – General → EAN/UPC `[VERIFY]` | UPC-A / EAN-13 check digit |

## 6.3 Assortment and listing

| Setting | Transaction / IMG | Value |
|---|---|---|
| Assortment types & listing procedures | SPRO → Assortment → Listing `[VERIFY]` | Assortment per store cluster (A/B/C) |
| Assortments | WSOA1 / WSOA2 | Z_CLUSTER_A … C; stores assigned |
| Listing | WSP4 (listing conditions) `[VERIFY]` | Automatic listing by MC and assortment |

## 6.4 Pricing and promotions

| Setting | Transaction / IMG | Value |
|---|---|---|
| Sales price condition type | V/06 | VKP0 (retail sales price) per distribution chain / site |
| Price calculation schema | SPRO → Pricing → Sales Price Calculation `[VERIFY]` | Planned markup by MC; price points .99 |
| Price point groups | SPRO → Price Point Groups `[VERIFY]` | Z_99: 0.99 / 4.99 / 9.99 endings |
| Sales price calculation | VKP5 / VKP2 | Mass calculation and release |
| Promotion types | SPRO → Promotion → Promotion Types `[VERIFY]` | Z_PROMO with promo price list |
| Promotions | WAK1 / WAK2 | PR-FALL: TS-100 at 15.00, store group A, 2 weeks |

## 6.5 Purchasing, replenishment and allocation

| Setting | Transaction / IMG | Value |
|---|---|---|
| Vendor BP roles & groupings | BP / BUCF | FLVN00, FLVN01; Y101 |
| Purchasing info records & conditions | ME11 / MEK1 | PB00; vendor discounts |
| Document types | OMEC | NB (standard), UB (stock transport), Z-allocation `[VERIFY]` |
| Stock transport order setup | SPRO → MM → Purchasing → PO → Set up STO | Shipping data for sites; delivery type NL; mvt 641/101 |
| Replenishment parameters | WR30 / WR60 `[VERIFY]` | Min/max per store; forecast-based at DC |
| Replenishment run | WRP1R | Daily 22:00 store; weekly DC |
| Allocation tables & rules | WA01 / WA21 `[VERIFY]` | Store quotas by cluster |
| EDI output | Output Management / NACE | ORDERS05 to vendors |

## 6.6 Store and DC operations

| Setting | Transaction / IMG | Value |
|---|---|---|
| EWM warehouse DC01 | /SCWM/LGNUM, /SCWM/MON | Inbound/outbound process types, storage types |
| Store apps | Fiori: receive products, transfer stock, count stock `[VERIFY app names]` | Roles for store manager/associate |
| Physical inventory | MI01 / MI04 / MI07 or Fiori | Cycle count by MC; tolerance per store |
| Movement types | OMJJ | 251/252 POS sales/returns, 641/101 STO, 701/702 inventory differences |

## 6.7 POS interface

| Setting | Transaction / IMG | Value |
|---|---|---|
| POS outbound profile | SPRO → POS Interface → Outbound → Profiles `[VERIFY]` | Z_STORE: prices, promotions, EAN, merchandise category |
| POS outbound processing | WPMA (manual), WPMI (initialisation) `[VERIFY]` | Change pointers daily 02:00 |
| POS inbound profile | SPRO → POS Interface → Inbound → Profiles `[VERIFY]` | WPUUMS (sales aggregated), WPUTAB (tenders), WPUFIB (FI), WPUBON (receipts – optional) |
| POS inbound monitor | WPER | Error handling per store/day |
| CAR / POS DTA | CAR configuration (/POSDW/*) | Inbound TLOG, sales audit tasks, outbound to S/4 |

## 6.8 Vendor rebates

| Setting | Transaction / IMG | Value |
|---|---|---|
| Condition contract types | SPRO → Settlement Management → Condition Contract `[VERIFY]` | Z_RBT: purchase rebate, accruals active |
| Condition contracts | WCOCO | CC-0001: vendor 1000700, 3% on purchases |
| Settlement | WB2R_SC | Monthly partial, annual final settlement |

## 6.9 Chart of accounts and finance integration

The account design is in [Chapter 5](05-chart-of-accounts.md); the settings below create it and connect logistics to the ledger.

| Setting | Transaction / IMG | Value |
|---|---|---|
| Chart of accounts | OB13 | YCOA – operational chart, 8-digit accounts, maintenance language EN |
| Assign chart to company code | OB62 | US10 → YCOA; country chart not used (US) |
| Account groups and number ranges | OBD4 | CASH 11000000–11999999 … SECC 94000000–96999999 (17 groups, see §5.2) |
| Field status variant / groups | OBC4 | Profit center required on P&L and inventory; tax code required on revenue |
| G/L accounts | FS00 / Fiori *Manage G/L Account Master Data* | 114 accounts from `finance/chart_of_accounts.csv` (mass load via Migration Cockpit *G/L account* `[VERIFY]`) |
| Cost elements | FS00 (type 1 primary / 42 assessment / 43 activity) | P&L accounts as primary cost elements; 94000000–96000000 secondary |
| Retained earnings | OB53 | Key X → 32000000 |
| Financial statement version | OB58 | FSV US10, nodes 1.1.1 … 8.0 as in §5.13 |
| Ledgers and currencies | FINSC_LEDGER | 0L leading (US GAAP); company code currency USD; group currency USD |
| Document splitting | GSP_RD | Splitting characteristics profit center (zero-balance), segment; method 0000000012 |
| Account determination (MM) | OBYC | BSX 13400000; WRX 21200000; PRD 50200000; GBB-VAX 50000000; GBB-INV 52300000; GBB-BSA 39990000 |
| Revenue determination (POS sales) | VKOA | ERL 41000000 (stores), 41000100 (online); ERS 41200000 (POS discounts); MWS 22000000 |
| Tender to G/L mapping | POS inbound FI settings `[VERIFY]` | Cash → 11009400; card → 11009500; gift card → 21500000 |
| Bank statement rules | OT83 / *Manage Bank Statement Reprocessing Rules* | Store deposits; acquirer settlement with fee 63600000 |
| Profit center derivation | Site master / document splitting | DC01 → 1100; ST01–ST50 → 2101–2150; WEB1 → 3100 |
| Rebate accounts | Settlement Management account determination `[VERIFY]` | 12600100 / 52500000 |
| Asset account determination | AO90 | Store fixtures 16400000; accumulated depreciation 17400000; POS & IT 16500000 / 17500000 |
| Migration clearing | FS00 + OBYC GBB-BSA | 39990000 – post-migration balance 0 (blocked for manual posting after go-live) |

> **Tip:** Load the chart of accounts from the same CSV that drives the ETL G/L mapping (`etl/config/mapping_rules.yaml`) and the worked example – one source of truth for the account design, the migration mapping and the test expectations.
