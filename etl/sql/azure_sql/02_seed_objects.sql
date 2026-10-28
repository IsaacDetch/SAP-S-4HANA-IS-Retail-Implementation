-- Migration object catalogue (sequence = docs/10-data-migration-azure-etl.md). Source queries are examples
-- against a legacy merchandising schema (LEGACY_MERCH) and general ledger (LEGACY_GL).
-- pl_10 extracts rows with a source_query; pl_30 loads rows with a gold_object to HANA staging in load_order.
INSERT INTO etl.migration_object (object_name, load_order, sap_object, source_query, gold_object, data_owner) VALUES
('stores',        1,  'Site (retail) [VERIFY]',                      'SELECT store_id, store_name, store_type, street, city, state, zip, country, open_date FROM LEGACY_MERCH.dbo.stores WHERE status = ''A''', 'site', 'Store operations'),
('vendors',       3,  'Supplier',                                    'SELECT vendor_id, name, street, city, state, zip, country, tax_id, bank_routing, bank_account, payment_terms FROM LEGACY_MERCH.dbo.vendors WHERE active = 1', 'supplier', 'Buying / AP'),
('items',         4,  'Article (retail) [VERIFY]',                   'SELECT style, style_desc, dept, class, color, size, upc, unit_cost, retail_price, vendor_id FROM LEGACY_MERCH.dbo.sku WHERE status IN (''A'',''C'')', 'article', 'Merchandising'),
('prices',        7,  'Condition record for pricing in sales',       NULL, 'sales_price', 'Pricing'),
('onhand',        12, 'Material inventory balance',                  'SELECT store_id, upc, qty_on_hand, unit_cost FROM LEGACY_MERCH.dbo.onhand_after_count', 'inventory_balance', 'Store & DC operations'),
('trial_balance', 14, 'FI – G/L account balance and open/line item', 'SELECT account AS legacy_account, cost_center AS store_id, debit, credit FROM LEGACY_GL.dbo.trial_balance WHERE period = ''2026-06''', 'gl_balance', 'Finance');
