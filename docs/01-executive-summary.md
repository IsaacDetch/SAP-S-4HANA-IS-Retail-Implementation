# 1. Executive Summary

[← Contents](../README.md#contents)

`[CLIENT]` Retail operates 50 stores, one distribution center and an online shop on a mix of legacy merchandising, POS back-office and finance systems. Prices and promotions are maintained in several places, store replenishment is largely manual, POS sales reach finance two to three days late, and vendor rebates are tracked in spreadsheets.

This plan implements **SAP IS-Retail** – delivered in S/4HANA as **SAP S/4HANA Retail for merchandise management** – as the single system for merchandise master data, buying, pricing and promotions, replenishment and allocation, store and DC inventory, POS sales integration, vendor rebates and finance. The plan covers every phase from business requirements to hypercare and steady-state production operations.

## 1.1 Objectives and success measures

| Objective | Measure | Target |
|---|---|---|
| Single source of article, price and promotion data | Price discrepancies at POS | < 0.1% of scanned items |
| Automated store replenishment | Share of store orders generated automatically | ≥ 85% |
| Daily store P&L | POS sales posted to G/L | By 06:00 the next day |
| Inventory accuracy | Store stock accuracy (cycle counts) | ≥ 97% |
| Vendor rebate capture | Rebates accrued vs. contractually due | 100% accrued monthly |
| Faster close | Month-end close | WD+4 |

## 1.2 Scope

| In scope | Out of scope (phase 2) |
|---|---|
| Merchandise category hierarchy, articles (generic & variants), sites, vendors | Fashion season & collection management (SAP S/4HANA for fashion) |
| Assortments, listing, sales price calculation, promotions | Customer loyalty and CRM |
| Purchasing, replenishment, allocation, stock transport orders | Unified demand forecasting & markdown optimisation |
| DC operations in EWM; store goods receipt, transfers and counts (Fiori) | Franchise and wholesale |
| POS outbound and inbound via CAR / POS DTA; sales audit | Store labour scheduling |
| Vendor rebates (condition contracts, Settlement Management) |  |
| Finance: AP, AR, cash & card settlement, inventory valuation, store P&L, financial statements |  |

## 1.3 Document structure

| Chapter | Content |
|---|---|
| [2](02-business-requirements.md) | Business requirements |
| [3](03-business-processes.md) | Business processes and process flows |
| [4](04-solution-design.md) | Solution architecture and design |
| [5](05-chart-of-accounts.md) | Chart of accounts and account determination |
| [6](06-configuration.md) | Configuration |
| [7](07-integration.md) | Integration |
| [8](08-finance-worked-example.md) | Finance integration and worked example to the financial statements |
| [9](09-testing.md) | Testing |
| [10](10-data-migration-azure-etl.md) | Data migration – Azure ETL to SAP Migration Cockpit staging tables |
| [11](11-cutover.md) | Cutover |
| [12](12-go-live-hypercare-production.md) | Go-live, hypercare and production operations |
| [13](13-project-plan.md) | Project plan, governance and risks |
| [14](14-glossary.md) | Glossary of abbreviations and terms |
| [App. A](appendix-a-transaction-codes.md) | Transaction code index |
