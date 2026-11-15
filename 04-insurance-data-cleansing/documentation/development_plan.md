# Project 04 — Development Plan

## Purpose

This plan records the agreed development sequence for the Insurance Data Cleansing Pipeline. Work is delivered incrementally, one source field at a time, with SQL implementation, validation evidence, exception handling and documentation updated as each stage is completed.

The project uses 100 synthetic policy records from two source systems.

## Delivery principles

1. Preserve raw source data as immutable evidence.
2. Use staging as the controlled working area.
3. Profile a field before defining its cleansing and validation rules.
4. Separate deterministic technical standardisation from business-approved corrections.
5. Revalidate after transformations; do not assume a correction has passed.
6. Keep validation status separate from exception investigation and resolution.
7. Retain exception and correction history.
8. Release a policy to the clean table only when every required field has passed.
9. Reconcile each field at field grain and the final output at policy grain.
10. Build the Power BI reporting layer from SQL views and reconcile dashboard measures to database results.

## Workstream 1 — Foundation and pipeline controls

| Activity | Deliverable | Status |
|---|---|---|
| Create MySQL database and core tables | Raw, staging, validation, exception, run-log and clean tables | Complete |
| Import synthetic source data | 100 source records | Complete |
| Populate staging | 100 working records | Complete |
| Establish pipeline run | Run-level execution record | Complete |
| Create validation snapshots | One row per source record per run | Complete |
| Create field-level exception register | Exception history and resolution status | Complete |
| Create clean output structure | Constrained target table | Complete |

## Workstream 2 — Field-by-field cleansing

The sequence below is a working delivery plan. Later fields remain pending until the preceding field has been profiled, its rules agreed, and its results reconciled.

| Sequence | Field / area | Planned work | Status |
|---:|---|---|---|
| 1 | Written Premium | Profile, standardise agreed formatting, validate and investigate exceptions | In progress — 94 Valid, 6 Outstanding |
| 2 | CurrencyCode | Profile case, whitespace, valid codes and unknown values; agree rules; cleanse and validate | Next |
| 3 | CommissionPct | Check numeric format, range, blanks and business plausibility | Planned |
| 4 | InceptionDate | Profile date formats, invalid dates and missing values | Planned |
| 5 | ExpiryDate | Profile date formats and validate relationship to inception date | Planned |
| 6 | ReportingYear | Validate numeric format and consistency with policy dates/business definition | Planned |
| 7 | Country | Standardise and validate against an agreed country reference list | Planned |
| 8 | Remaining policy attributes | Confirm required fields, profile, define rules and validate | Planned |

### Written Premium — current evidence

Initial profiling:
- 77 records matched the agreed numeric format.
- 23 records did not match the agreed format.

After agreed staging transformations and revalidation:
- 94 records are Valid.
- 6 records remain Exception.
- 17 original exception records passed revalidation and were marked Resolved.
- 6 remain Outstanding: RawRecordIDs 18, 24, 31, 67, 85 and 94.
- The outstanding values comprise two blanks, two `TBC` placeholders and two whitespace-only values.

No value has been assumed for the six outstanding records. Replacing them with zero is not a technical formatting decision; it requires business confirmation that zero is correct.

### CurrencyCode — next work session

Planned sequence:

1. Profile distinct raw and staging CurrencyCode values.
2. Identify whitespace, case differences, blanks, placeholders and unrecognised codes.
3. Compare candidate values with an agreed ISO 4217 currency-code reference.
4. Agree which changes are safe technical standardisation (for example, trimming and uppercasing a recognised code).
5. Keep unknown values and ambiguous cases as exceptions for investigation.
6. Apply approved changes to staging only.
7. Update CurrencyCode validation status for the active pipeline run.
8. Reconcile validation counts against the exception register.
9. Document the rule, script sequence and results before moving to the next field.

CurrencyCode must be treated as a separate field from Written Premium formatting. A currency symbol appearing in the premium text does not, by itself, prove which currency code should be assigned.

## Workstream 3 — SQL reporting layer

Create reusable SQL views after the relevant table structures and status conventions are stable.

Proposed views:

| View | Purpose |
|---|---|
| `vw_pipeline_run_summary` | Records processed, run outcome and run timestamps |
| `vw_field_validation_summary` | Valid, Exception and Pending counts by field and run |
| `vw_exception_summary` | Outstanding, Resolved and Closed exceptions by field/type |
| `vw_exception_detail` | Record-level exception details for investigation |
| `vw_policy_quality_status` | Whole-policy status based on all required field validations |
| `vw_reconciliation_summary` | Raw, staging, validated and clean record counts |

These are proposed view names; confirm actual columns and relationships before implementation. Avoid double-counting policies when joining multiple field-level exceptions.

## Workstream 4 — Power BI dashboard

Connect Power BI to the MySQL reporting views once the first reporting layer is available. Build the dashboard iteratively rather than waiting for all fields to be complete.

Planned pages:

1. Executive Overview
2. Field Validation
3. Exception Management
4. Reconciliation
5. Pipeline & Audit

See [Power BI Dashboard Concept](./powerbi_dashboard_concept.md) for the proposed layout and measures.

## Workstream 5 — Final release and QA

1. Complete validation of every required field.
2. Resolve or explicitly retain all outstanding exceptions with documented business disposition.
3. Confirm whole-policy status at one row per policy.
4. Load only fully validated policies to `clean_policy_data`.
5. Reconcile source records to clean records and outstanding policy exceptions.
6. Test reruns, duplicate prevention, transaction handling and audit history.
7. Confirm Power BI totals reconcile to SQL results.
8. Complete project documentation and evidence.

## Definition of done

The pipeline is complete when all source records are accounted for, each transformation has a documented rule or approved decision, unresolved values remain visible, the clean table contains only fully validated policies, audit history is retained, reconciliations balance, and the Power BI dashboard accurately reports the SQL results.
