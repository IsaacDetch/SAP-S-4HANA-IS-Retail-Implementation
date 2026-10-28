# 9. Testing

[← Contents](../README.md#contents)

## 9.1 Test strategy

| Test phase | Scope | Environment | Entry / exit criteria | Owner |
|---|---|---|---|---|
| Unit test | Each configuration item & development object | DEV | Config complete / test evidence in ALM | Functional consultant |
| String test | Process segments (e.g. PO → GR → invoice) | DEV/QA | Unit tests passed / no sev-1 | Workstream lead |
| SIT 1 | End-to-end processes incl. interfaces with test POS and EDI | QA | Mock load 1 data / ≥ 95% pass, no sev-1 | Test lead |
| SIT 2 | Full scope incl. CAR, EWM, banks, month-end close | QA | Mock load 2 / 100% executed, no sev-1/2 | Test lead |
| Performance | POS inbound volume, replenishment run, POS outbound, EWM waves | PRE-PROD | Production-size data / NFR-01–03 met | Basis / test lead |
| UAT | Business acceptance per role, day-in-the-life of store & DC | QA | SIT exit / business sign-off | Business process owners |
| Store pilot rehearsal | Model store with real POS terminals, scanners, printers | QA + lab store | Devices certified / 3 trading days simulated | Store operations |
| Regression | Automated core scenarios after each transport wave | QA | Before each release | Test automation |
| Cutover rehearsal | Full cutover runbook incl. timings | PRE-PROD | Mock 3 / within cutover window | Cutover manager |

## 9.2 Integration test scenarios

| ID | Scenario | Expected result |
|---|---|---|
| SIT-R01 | Create generic article with variants, list to cluster A, calculate price, download to POS | Variants & EANs created; listed in 20 stores; price 19.99 rounded; POS file contains article |
| SIT-R02 | DC replenishment → PO → EDI ORDERS → DESADV → EWM GR → EDI INVOIC → MIRO | GR value 8,000.00; invoice matched; rebate accrual 240.00 |
| SIT-R03 | Store replenishment → STO → EWM pick → GI 641 → store GR (Fiori) | Inventory value 4,800.00 moves to ST01 / PC 2101 |
| SIT-R04 | Promotion PR-FALL created and active at POS on start date | POS sells at 15.00 in cluster A only |
| SIT-R05 | POS day with sales, return, cash and card tenders → CAR audit → S/4 | Revenue 8,800.00; COGS 3,920.00; tenders cleared |
| SIT-R06 | POS IDoc error (unknown EAN) → correction in CAR → reprocess | Error visible in WPER/CAR; reprocessed successfully |
| SIT-R07 | Store cycle count with difference | Shrinkage 40.00 posted to 52300000 / store |
| SIT-R08 | Card acquirer settlement & cash deposit bank statement | Auto-matched; fee to 63600000 |
| SIT-R09 | Allocation of new season article to stores by cluster quota | STOs per store as per allocation table |
| SIT-R10 | Online order fulfilled from DC; customer return to store | Stock & revenue posted in correct sites |
| SIT-R11 | Condition contract settlement | Settlement document credits vendor; receivable cleared |
| SIT-FIN-01 | Month-end close and store P&L | Net income 1,664.00; balance sheet balances ([§8.7](08-finance-worked-example.md)) |

## 9.3 Defect management

| Severity | Definition | Resolution target |
|---|---|---|
| 1 – Critical | Blocks trading, POS posting or payments; no workaround | 4 hours, fix before next test day |
| 2 – High | Major function impaired; workaround hard | 2 days |
| 3 – Medium | Function impaired; workaround exists | Before UAT exit |
| 4 – Low | Cosmetic | Backlog |
