# BDX Runoff — Logical Entity Relationship Diagram

This simplified logical ERD illustrates the main entities and relationships supporting Written BDX settlement and Paid BDX export processing.

The diagram is a portfolio-level representation of the business relationships, not a physical database specification.

```mermaid
erDiagram
    WRITTEN_BDX_TRANSACTION ||--o{ PAYMENT : "has"
    PAYMENT_IMPORT ||--o{ PAYMENT : "contains"
    PAYMENT ||--o{ PAID_BDX_BATCH_ITEM : "allocated through"
    PAID_BDX_BATCH ||--|{ PAID_BDX_BATCH_ITEM : "contains"
    PAID_BDX_BATCH ||--o{ PAID_BDX_EXPORT : "has export history"

    WRITTEN_BDX_TRANSACTION {
        string TransactionID PK
        decimal TotalPremiumPayable
        decimal PaymentReceived
        decimal RemainingToPay
        string SettlementStatus
    }

    PAYMENT_IMPORT {
        string ImportID PK
        date ImportDate
        int RecordCount
        string Status
    }

    PAYMENT {
        string PaymentID PK
        string ImportID FK
        string TransactionID FK
        decimal PaymentAmount
        date PaymentDate
        boolean Applied
    }

    PAID_BDX_BATCH {
        string PaidBatchID PK
        int ReportingYear
        int ReportingMonth
        string SettlementCurrency
        int RecordCount
    }

    PAID_BDX_BATCH_ITEM {
        string BatchItemID PK
        string PaidBatchID FK
        string PaymentID FK
        decimal AmountAllocated
    }

    PAID_BDX_EXPORT {
        string ExportID PK
        string PaidBatchID FK
        date ExportDate
        string ExportType
        string ExportStatus
    }
```

## Relationship Notes

- A Written BDX transaction can have multiple payments.
- An import can contain multiple payment records.
- Payments are linked to batches through allocation records.
- A batch can have multiple export events, including regeneration.
- The allocation entity preserves the history of which payments were included in each batch.

## Design Note

Entity and attribute names are illustrative portfolio names. The diagram simplifies the original business model and does not define every field, constraint, or physical implementation detail.
