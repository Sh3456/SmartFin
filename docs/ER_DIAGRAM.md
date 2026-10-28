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

## Relationship notes

- One location can be associated with many devices, customers, and merchants.
- A customer can make many transactions; each transaction references one customer, merchant, and device when that information is available.
- A transaction can have zero or more chargebacks and fraud alerts.
- The `TRANSACTIONS` table is the central fact table; the other tables provide customer, merchant, device, location, dispute, and review context.
- Use the foreign keys and indexes in `oracle/01_schema.sql` to preserve relationships and support common joins.
