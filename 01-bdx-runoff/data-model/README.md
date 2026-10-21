# BDX Runoff — Logical Data Model

## 1. Purpose

This section describes the main data entities and relationships required to support the BDX runoff settlement and Paid BDX export process.

The logical data model connects the business process to the information required for payment processing, settlement calculations, batch allocation, export generation, and auditability.

It describes the business purpose of the data entities without prescribing a specific vendor's physical database implementation.

## 2. Core Data Entities

### Written BDX Transaction

**Purpose:** Stores the original Written BDX transaction and its current payment position.

Key information includes the transaction identifier, payable amount, cumulative payments received, remaining balance, and settlement status.

### Payment Staging

**Purpose:** Provides a temporary landing area for payment rows before they are processed.

Staging allows incoming data to be checked before it becomes part of the controlled payment history.

### Payment Import

**Purpose:** Records an imported payment population and its associated control information.

Examples include an import identifier, import date, filename, record count, and processing status.

### Payment Ledger

**Purpose:** Maintains the official history of individual payments and their application status.

Each payment is linked to the relevant Written BDX transaction and import.

### Paid BDX Batch

**Purpose:** Represents a controlled group of eligible payments prepared for reporting.

Batch information includes the batch identifier, reporting period, settlement currency, record count, and relevant creation details.

### Paid BDX Batch Item

**Purpose:** Records the allocation of a payment to a Paid BDX batch.

This entity provides traceability between individual payments and the batches in which they are reported.

### Paid BDX Export

**Purpose:** Records each export event associated with a Paid BDX batch.

It distinguishes original exports from regenerated exports and supports audit and reproduction of existing batches.

## 3. Principal Relationships

The logical model supports the following relationships:

- One Written BDX transaction can have multiple payments.
- One payment import can contain multiple payment records.
- One Paid BDX batch can contain multiple payment allocations.
- Payment allocation records link individual payments to Paid BDX batches.
- One Paid BDX batch can have multiple export events.
- A transaction may be represented in multiple batches when separate payments are processed at different times.

These relationships support payment traceability, settlement processing, batch creation, and export audit history.

## 4. Key Data Integrity Rules

The model must support the following business controls:

- Payments must reference an existing Written BDX transaction.
- Cumulative payments must not exceed the total payable amount.
- Remaining balance and settlement status must reflect the payment position.
- Only applied, previously unallocated payments are eligible for new Paid BDX processing.
- Duplicate allocation of a payment to a new batch must be prevented.
- Allocation amounts must reconcile to the applicable payment amounts.
- Export history must retain the relationship to the original batch.
- Regenerating an export must not create a new batch or reprocess payments.

## 5. Relationship to SQL Validation

The logical model provides the foundation for SQL checks covering:

- Payments with missing or invalid transaction references.
- Incorrect settlement balances or statuses.
- Potential overpayments.
- Duplicate payment allocations.
- Differences between payment amounts and allocated amounts.
- Batches with no eligible payment allocations.
- Export records without a valid batch reference.

These checks will be developed using synthetic data in the SQL validation section.

## 6. Scope and Design Boundaries

The model is a logical representation of the business entities and relationships. Exact physical table structures, keys, constraints, indexes, and implementation details remain subject to detailed solution design.

The Accounts integration and bank reconciliation workflow are separate design considerations. BDX settlement status must not be treated as equivalent to bank reconciliation status.

## 7. Status

**In progress.** The principal entities and business relationships have been identified. A visual logical data model and supporting SQL validation examples will be added as the project develops.

## 8. Confidentiality

This is a sanitised portfolio description. Supporting diagrams and examples will use synthetic or appropriately anonymised information and will not reproduce confidential company documents.
