# 7. Integration

[← Contents](../README.md#contents)

| ID | Interface | Direction | Technology | Frequency |
|---|---|---|---|---|
| INT-R01 | Prices, promotions, EAN, MC to POS | S/4 → POS | IDoc (WP_PLU, WPDWGR, WP_EAN `[VERIFY]`) via BTP | Daily 02:00 + ad hoc |
| INT-R02 | TLOG from POS | POS → CAR | File / API | Near real time / end of day |
| INT-R03 | Aggregated sales, tenders, FI | CAR → S/4 | IDoc WPUUMS, WPUTAB, WPUFIB | Daily 01:00–05:00 |
| INT-R04 | Purchase orders | S/4 → vendors | EDI ORDERS via BTP | On PO release |
| INT-R05 | Advance shipping notices | Vendors → S/4/EWM | EDI DESADV | On shipment |
| INT-R06 | Vendor invoices | Vendors → S/4 | EDI INVOIC | On invoice |
| INT-R07 | Bank statements & card settlements | Banks → S/4 | camt.053 / acquirer file | Daily |
| INT-R08 | Online orders & availability | Commerce ↔ S/4 | APIs via BTP | Real time |
| INT-R09 | Analytics | S/4, CAR → SAC/Datasphere | Live / replication | Hourly |
