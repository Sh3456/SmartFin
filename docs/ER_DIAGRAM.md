# ER Diagram — Fintech Fraud Analytics

```mermaid
erDiagram
  LOCATIONS ||--o{ DEVICES : located_at
  LOCATIONS ||--o{ CUSTOMERS : primary_location
  LOCATIONS ||--o{ MERCHANTS : primary_location
  CUSTOMERS ||--o{ TRANSACTIONS : makes
  MERCHANTS ||--o{ TRANSACTIONS : receives
  DEVICES ||--o{ TRANSACTIONS : used_for
  TRANSACTIONS ||--o{ CHARGEBACKS : may_receive
  TRANSACTIONS ||--o{ FRAUD_ALERTS : may_trigger
```

One location can serve many devices, customers, and merchants. A customer, merchant, or device can be linked to many transactions. A transaction can have zero or more chargeback records and fraud alerts. Transactions form the central fact table, while the other tables provide context for analysis.

The Oracle constraints and indexes are defined in `oracle/01_schema.sql`.
