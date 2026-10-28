# 14. Glossary of Abbreviations and Terms

[← Contents](../README.md#contents)

## 14.1 Abbreviations

| Abbreviation | Meaning |
|---|---|
| AA | Asset Accounting (SAP FI-AA) |
| ADF | Azure Data Factory – cloud orchestration and data movement service |
| ADLS Gen2 | Azure Data Lake Storage Gen2 – hierarchical-namespace storage for the data lake |
| AMS | Application Management Services – post-go-live support provider |
| AP / AR | Accounts Payable / Accounts Receivable |
| ATTYP | Article category field (00 single, 01 generic, 02 variant, 10 sales set, 11 prepack) |
| BP | Business Partner – S/4HANA master record for suppliers and customers |
| BR | Business requirement (IDs BR-xx-nn in Chapter 2) |
| BSX / WRX / PRD / GBB | OBYC transaction keys: inventory posting / GR/IR clearing / price differences / offsetting entry for inventory posting |
| BTP | SAP Business Technology Platform (Integration Suite for interfaces) |
| CAR | SAP Customer Activity Repository – POS data hub with sales audit (POS DTA) |
| CDS | Core Data Services – S/4HANA virtual data model views used for reporting and reconciliation |
| CO | Controlling (cost centers, profit centers, internal orders) |
| COGS | Cost of goods sold |
| CoA | Chart of accounts |
| DC | Distribution center (site category B) |
| DESADV / ORDERS / INVOIC | EDI messages: despatch advice / purchase order / invoice |
| DQ | Data quality |
| DTA | Data Transfer and Audit (POS DTA in CAR) |
| EAN / GTIN / UPC | European Article Number / Global Trade Item Number / Universal Product Code – barcode identifiers (GS1) |
| EDI | Electronic Data Interchange |
| ERL / ERS / MWS | VKOA account keys: revenue / sales deductions / output tax |
| ETL | Extract, transform, load |
| EWM | SAP Extended Warehouse Management |
| FI | Financial Accounting |
| FSV | Financial statement version |
| GI / GR | Goods issue / goods receipt |
| GR/IR | Goods receipt / invoice receipt clearing account |
| GS1 | Global standards body for barcodes; defines the GTIN check digit |
| HANA | SAP in-memory database underlying S/4HANA |
| IDoc | Intermediate Document – SAP message format (e.g. WPUUMS, WPUTAB, WPUFIB for POS inbound) |
| IMG / SPRO | Implementation Guide – SAP configuration menu |
| IR / SHIR | (Self-hosted) integration runtime in Azure Data Factory |
| IS-Retail | SAP Industry Solution Retail – in S/4HANA: SAP S/4HANA Retail for merchandise management |
| JDBC / ODBC | Database connectivity standards used to write to HANA staging tables |
| KPI | Key performance indicator |
| MC | Merchandise category |
| MIGO / MIRO | Goods movement / supplier invoice transactions |
| NRV | Net realisable value |
| OBYC / VKOA | Account determination for inventory postings / for revenue (SD and POS) |
| OData | Open Data Protocol – REST API used to read S/4HANA for reconciliation |
| P&L | Profit and loss statement |
| PO / STO | Purchase order / stock transport order |
| POS | Point of sale |
| RACI | Responsible, Accountable, Consulted, Informed |
| RF | Radio frequency (handheld scanner in DC) |
| ROU | Right-of-use asset (leases) |
| SIT / UAT | System integration test / user acceptance test |
| SKU | Stock keeping unit – a variant article |
| TLOG | Transaction log – POS sales file from the till |
| VKP0 | Standard sales price condition type in retail |
| VLFKZ | Site category field (A = store, B = distribution center) |
| WD+n | Working day n of the next month (close calendar) |
| YCOA | SAP Best Practices operational chart of accounts |

## 14.2 Terms

| Term | Meaning |
|---|---|
| Allocation | Distribution of a quantity of merchandise (e.g. new season, promotion) to stores by rules |
| Assortment / listing | The set of articles a site may sell; listing creates the article–site link required for POS and replenishment |
| Bronze / silver / gold | Medallion lake layers: raw copy / cleansed legacy structure / SAP-ready migration layout |
| Condition contract | Settlement Management agreement with a vendor for rebates and funding; accrues on invoices and settles periodically |
| Cutover | The controlled sequence of freeze, final loads, count and switch from legacy to S/4HANA |
| Document splitting | Real-time splitting of G/L lines by profit center/segment so each store has a balanced balance sheet |
| Generic article | Parent article (e.g. TS-100 Basic Tee) carrying common data; its variants are colour/size combinations |
| Go / no-go | Formal decision meeting before go-live against agreed criteria |
| Hypercare | Intensive support period after go-live with war room and KPIs |
| Load gate | Automated decision in ADF that allows the HANA staging load only if DQ and reconciliation pass |
| Medallion architecture | Layered lakehouse design (bronze → silver → gold) |
| Migration Cockpit | S/4HANA tool for data migration (Fiori app *Migrate Your Data*), using files or staging tables |
| Migration clearing account | 39990000 – technical account that balances the stock and G/L loads; must be zero after migration |
| Mock load | Full rehearsal of the migration in a test system |
| Moving average cost | Inventory valuation where the unit cost is recalculated on each receipt (price control V) |
| Price point | Customer-facing price ending (.99, .00) applied by price calculation |
| Profit center | CO object per store/DC used for store P&L and balance sheet |
| Replenishment | Automatic calculation of order quantities for DC (from vendors) and stores (from DC) |
| Sales audit | Validation and correction of POS data in CAR before posting to S/4HANA |
| Shrinkage | Unexplained inventory loss found by counts (theft, damage, errors) |
| Site | Retail plant: store, DC or online channel, created from a site profile |
| Staging table | HANA table generated by the Migration Cockpit and filled by the ETL before the migration run |
| Tender | Means of payment at POS (cash, card, gift card) |
| Variant | Saleable colour/size version of a generic article with its own EAN |
| Wave | Group of stores going live together after the pilot |
