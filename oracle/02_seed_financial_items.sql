-- Seed the small financial dictionary used by SmartFin's MVP.
-- MERGE makes this script safe to re-run.

MERGE INTO FINANCIAL_ITEM T
USING (
    SELECT 'CURRENT_ASSETS' ITEM_CODE, 'Current assets' ITEM_NAME, 'ASSET' CATEGORY,
           'Used in current ratio and working capital.' FORMULA_NOTES FROM DUAL
    UNION ALL SELECT 'CURRENT_LIABILITIES', 'Current liabilities', 'LIABILITY',
           'Denominator of current/quick ratio; also used in working capital.' FROM DUAL
    UNION ALL SELECT 'INVENTORY', 'Inventories', 'ASSET',
           'Subtracted from current assets in SmartFin MVP quick-ratio formula.' FROM DUAL
    UNION ALL SELECT 'REVENUE', 'Revenue from operations', 'INCOME',
           'Used for optional net profit margin.' FROM DUAL
    UNION ALL SELECT 'NET_PROFIT', 'Profit for the year', 'PROFIT',
           'Used for optional net profit margin; can be negative.' FROM DUAL
    UNION ALL SELECT 'TOTAL_DEBT', 'Total debt / borrowings', 'LIABILITY',
           'Optional input for debt-to-equity analysis.' FROM DUAL
    UNION ALL SELECT 'EQUITY', 'Total equity', 'EQUITY',
           'Optional denominator for debt-to-equity analysis.' FROM DUAL
    UNION ALL SELECT 'OPERATING_CASH_FLOW', 'Net cash from operating activities', 'CASH_FLOW',
           'Optional operating cash-flow indicator; can be negative.' FROM DUAL
) S
ON (T.ITEM_CODE = S.ITEM_CODE)
WHEN MATCHED THEN UPDATE SET
    T.ITEM_NAME = S.ITEM_NAME,
    T.CATEGORY = S.CATEGORY,
    T.FORMULA_NOTES = S.FORMULA_NOTES,
    T.IS_ACTIVE = 'Y'
WHEN NOT MATCHED THEN INSERT
    (ITEM_CODE, ITEM_NAME, CATEGORY, FORMULA_NOTES, IS_ACTIVE)
VALUES
    (S.ITEM_CODE, S.ITEM_NAME, S.CATEGORY, S.FORMULA_NOTES, 'Y');

COMMIT;
