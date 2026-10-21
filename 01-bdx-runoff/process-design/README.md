# BDX Runoff — Process Design

## 1. Purpose

This section describes the high-level business process for applying payments to Written BDX transactions and producing controlled Paid BDX reporting outputs.

The process design translates business requirements into a sequence of operational stages, highlighting key decisions, controls, and relationships between transactions, payments, batches, and exports.

## 2. End-to-End Process

### Step 1 — Written BDX Transaction

The Written BDX transaction provides the starting financial position against which subsequent payments are recorded.

**Key consideration:** The original transaction must remain traceable throughout the payment and reporting lifecycle.

### Step 2 — Payment File Preparation

Payment information is prepared for controlled import into the settlement process.

**Key consideration:** The incoming payment population must be identifiable and suitable for validation.

### Step 3 — Controlled Payment Import

The payment data is imported into the payment-processing workflow, with import-level controls such as an import identifier and record count.

**Key controls:**
- Record the identity of the import.
- Validate the source transaction reference.
- Check the imported record population.
- Identify invalid or duplicate submissions.

### Step 4 — Payment Validation and Application

Payments are validated before being accepted and applied to their corresponding Written BDX transactions.

The process must support multiple payments against one transaction and prevent cumulative payments from exceeding the amount payable.

**Key controls:**
- Confirm that the source transaction exists.
- Validate payment information.
- Prevent overpayment.
- Retain the status and history of payment application.

### Step 5 — Update the Settlement Position

Following payment application, the transaction's cumulative amount received, remaining balance, and settlement status are updated.

The business process distinguishes three settlement states:

- **No** — no payment has been received.
- **Partial** — some payment has been received, but a balance remains.
- **Settled** — the full payable amount has been received and the remaining balance is zero.

**Important distinction:** BDX settlement status does not, by itself, confirm that cash has cleared or been reconciled by the bank.

### Step 6 — Identify Eligible Payments

The process identifies payments that have been successfully applied and have not already been allocated to a Paid BDX batch.

Payments that fail validation or have already been allocated must not be processed again as new batch items.

### Step 7 — Create the Paid BDX Batch

Eligible payments are grouped into a Paid BDX batch according to the agreed reporting period and settlement currency.

The batch records relevant control information, such as its identifier, reporting period, currency, record count, and creation details.

### Step 8 — Record Payment Allocations

The relationship between each payment and its Paid BDX batch is recorded.

This allocation history supports traceability, reconciliation, and the prevention of duplicate allocation. A transaction may be represented across multiple batches when its payments are processed at different times.

### Step 9 — Produce the Paid BDX Output

The selected batch is used to produce the required Paid BDX reporting output.

The output must follow the agreed field structure and applicable reporting requirements. Required fields and configured validation rules should be checked before the output is accepted for operational use.

### Step 10 — Record Export History

Each export event is recorded so that the output can be traced to the batch from which it was generated.

The process distinguishes the original export from subsequent regenerations of the same batch.

### Step 11 — Regenerate an Existing Batch

An existing Paid BDX batch can be regenerated using its existing batch identifier.

Regeneration must not create a new batch or reprocess the underlying payments. It must use the existing payment-to-batch allocation history and record the new export event.

## 3. Key Process Controls

| Control | Business purpose |
|---|---|
| Import identification and record counts | Establish control over the incoming payment population. |
| Source transaction validation | Prevent payment application to unknown transactions. |
| Overpayment prevention | Protect the integrity of the settlement position. |
| Settlement status calculation | Represent the payment position accurately. |
| Applied and unallocated payment checks | Restrict batch creation to eligible payments. |
| Allocation history | Maintain traceability between payments and batches. |
| Allocation reconciliation | Check that allocated amounts agree with the applicable payment amounts. |
| Duplicate prevention | Avoid duplicate imports, applications, or allocations. |
| Export audit history | Record original exports and subsequent regenerations. |
| Output validation | Check the reporting output against the agreed specification. |

## 4. Process Exceptions

The process must identify and handle exceptions in a controlled way.

Examples include:

- A payment refers to an unknown transaction.
- A payment would cause an overpayment.
- An import contains no payment rows.
- No eligible payments are available for batch creation.
- A payment has already been allocated to a batch.
- An export is requested for an invalid or empty batch.
- Required output data is missing or fails validation.
- The same import is submitted more than once.

Exceptions should be traceable and available for investigation. Failed processing should not leave duplicate or partially processed financial records.

## 5. Business Process Boundaries

The BDX process is responsible for payment application, settlement position, Paid BDX batching, allocation history, and export controls.

Where a separate Accounts system is involved, it retains responsibility for accounting treatment. BDX settlement and bank reconciliation remain distinct control outcomes.

## 6. Design Considerations and Open Questions

The following items require confirmation during detailed solution design where they apply:

- Final technical implementation and production architecture.
- Exact physical export format and delivery mechanism.
- Detailed output-field mapping and applicable validation rules.
- Migration scope, mapping, and reconciliation controls.
- Interface and exception-handling arrangements with the Accounts system.
- Detailed bank reconciliation workflow and its implementation scope.

These items should be treated as design considerations rather than assumed to be fully resolved by the high-level process.

## 7. Relationship to Other Project Sections

- **Requirements:** Defines the business objectives, requirements, and acceptance criteria.
- **Data model:** Describes the entities and relationships needed to support the process.
- **SQL validation:** Will demonstrate how data quality, settlement calculations, allocation integrity, and reconciliation can be tested.

## 8. Status

**In progress.** This document describes the high-level process. Detailed process diagrams, data relationships, and SQL validation examples will be developed as the project progresses.

## 9. Confidentiality

This is a sanitised portfolio description. It does not reproduce the original business requirements document or disclose confidential company-specific information. Any supporting examples will use synthetic or appropriately anonymised data.
