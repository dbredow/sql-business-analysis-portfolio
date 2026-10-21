# BDX Runoff — SQL Validation

## 1. Purpose

This section demonstrates how SQL can be used to validate settlement data, test business rules, identify exceptions, and reconcile payments to Paid BDX batch allocations.

The examples will use synthetic data and are intended to demonstrate business-focused SQL problem-solving rather than access or reproduce a production database.

## 2. Validation Areas

### 2.1 Payment-to-Transaction Validation

**Business question:** Are all payments linked to a valid Written BDX transaction?

SQL checks will identify payments whose transaction reference does not match an existing transaction.

### 2.2 Settlement Balance Validation

**Business question:** Do the payment totals, outstanding balance, and settlement status agree?

The checks will compare the total payable amount with cumulative payments received and the remaining balance.

Expected relationship:

`RemainingToPay = TotalPremiumPayable - PaymentReceived`

The settlement status should reflect whether no payment, partial payment, or full settlement has occurred.

### 2.3 Overpayment Detection

**Business question:** Has the cumulative payment amount exceeded the amount payable?

The validation will identify transactions where cumulative payments exceed the agreed payable amount.

### 2.4 Paid BDX Batch Eligibility

**Business question:** Does each new batch contain only eligible payments?

The checks will identify payments that have not been applied successfully or have already been allocated to a batch.

### 2.5 Allocation Reconciliation

**Business question:** Do payment amounts reconcile to the amounts allocated to Paid BDX batches?

The checks will compare the applicable payment amounts with their allocation records and flag unexplained differences.

### 2.6 Duplicate Allocation Detection

**Business question:** Has a payment been allocated more than once when it should only be allocated once?

The validation will identify duplicate allocation records for investigation.

### 2.7 Batch and Export Validation

**Business question:** Does each export refer to a valid batch containing eligible allocation records?

The checks will identify missing batch references, empty batches, and export records that require investigation.

### 2.8 Import Control Validation

**Business question:** Does the imported payment population agree with the expected record count?

The checks will compare the recorded import count with the actual imported population and identify discrepancies.

## 3. Planned SQL Techniques

The portfolio examples may use:

- `JOIN` operations to compare related entities.
- `GROUP BY` and aggregate functions to calculate payment totals.
- `CASE` expressions to classify settlement positions.
- Common Table Expressions (CTEs) to organise complex validation logic.
- Subqueries to identify exceptions.
- Duplicate checks and reconciliation queries.

## 4. Test Data and Expected Results

Synthetic data will include valid transactions alongside deliberately introduced exceptions, such as:

- An unknown transaction reference.
- An overpayment.
- An incorrect remaining balance.
- A payment already allocated to a batch.
- A payment-to-allocation difference.
- A duplicate allocation.
- An import record-count mismatch.

Each SQL example will explain the business question, the validation logic, and the expected result.

## 5. Relationship to Acceptance Criteria

The validation queries will support the proposed acceptance criteria in the Requirements section. The results will be used to demonstrate whether the defined business rules hold and whether exceptions can be identified.

## 6. Status

**In progress.** Validation scenarios have been identified. Synthetic test data, SQL scripts, and expected results will be added as the proof of concept develops.

## 7. Confidentiality

All published examples will use synthetic or appropriately anonymised data. Confidential company information and production data will not be included.
