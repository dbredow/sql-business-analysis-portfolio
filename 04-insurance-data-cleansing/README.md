# Project 04 — Insurance Data Cleansing Pipeline

## Project overview

Build a repeatable, auditable SQL data-cleansing pipeline for insurance policy data received from multiple source systems.

The project starts with a 100-row synthetic dataset containing deliberately inconsistent, incomplete and potentially invalid values. The aim is to turn that raw input into a validated, reporting- or migration-ready dataset without losing the original source information or silently inventing business answers.

This is a practical end-to-end pipeline project covering business analysis, data profiling, transformation, validation, exception management, loading, reconciliation and repeatable execution.

All dataset records are synthetic.

## Business objectives

- Understand the quality and structure of incoming policy data.
- Identify completeness, validity, consistency and uniqueness issues.
- Agree data treatments with the business where technical rules alone cannot determine the correct answer.
- Preserve raw source values and make every transformation traceable.
- Standardise valid data using documented, repeatable rules.
- Isolate unresolved or invalid records for investigation.
- Produce a clean dataset suitable for downstream reporting or migration.
- Reconcile records across the pipeline and demonstrate safe reruns.

## Dataset

The initial dataset contains 100 synthetic policy records from two source systems. Fields include source identifiers, policy references, broker and insured names, policy status, raw inception and expiry dates, written premium, currency, commission percentage, reporting year, country and import metadata.

The data deliberately includes inconsistent date formats, mixed case and spacing, missing values, free-text entries, inconsistent representations and values requiring validation.

## Pipeline architecture

`raw_policy_data` → `stg_policy_data` → validation and routing → `clean_policy_data`

Records that cannot pass the agreed validation rules are recorded in an exception layer rather than silently corrected or discarded.

### 1. Raw layer

- Retain source values exactly as received.
- Preserve source identifiers and import-batch metadata.
- Do not apply destructive updates to raw records.

### 2. Staging layer

- Apply approved formatting and standardisation rules.
- Retain original values alongside transformed values where needed.
- Capture validation results and field-level status.
- Keep transformations reproducible.

### 3. Validation and exception management

- Test required fields, data types, formats, ranges and business rules.
- Distinguish missing, invalid, ambiguous and not-applicable values.
- Record exception reasons and resolution status.
- Use business-approved decisions where a value cannot be safely inferred.

### 4. Clean output

- Load records that satisfy the agreed acceptance rules.
- Enforce appropriate keys and data integrity constraints.
- Retain traceability to the source record and import batch.

### 5. Reconciliation and audit

- Account for every source record.
- Reconcile clean records, exceptions and any explicitly excluded records.
- Record pipeline execution and batch outcomes.
- Demonstrate that rerunning a batch does not create duplicates or corrupt prior results.

## Business rules and governance

The project distinguishes technical standardisation from business correction.

Examples:
- Trimming whitespace and converting a currency code to uppercase can be deterministic formatting rules.
- Replacing a missing currency, interpreting an ambiguous date or correcting a premium requires evidence or an approved business decision.
- Unknown or unsupported values remain visible as exceptions until resolved.

Business decisions and transformation rules will be documented so that the pipeline can be rerun consistently and its outputs explained.

## One-week delivery plan

| Day | Focus | Intended deliverable |
|---|---|---|
| 1 | Complete profiling and identify business questions | Profiling report and business questions |
| 2 | Define transformation and validation rules | Data-cleansing rules register |
| 3 | Design and create database layers | Staging, clean, exception and supporting tables |
| 4 | Build the first end-to-end pipeline | Initial repeatable SQL run |
| 5 | Validate and reconcile | Validation results and reconciliation report |
| 6 | Implement batch-safe reruns and automation | Stored procedure or controlled execution script |
| 7 | End-to-end QA and portfolio documentation | Demonstration, process map and completed project documentation |

The one-week target is to deliver a working and tested pipeline. Any business decisions not received by the end of the build remain explicitly unresolved exceptions; they will not be guessed to meet the deadline.

## Acceptance criteria

The project will be considered complete when:

1. All 100 source records are accounted for by the pipeline.
2. Each transformation is supported by a documented technical rule or business-approved decision.
3. Unresolved and invalid records are routed to an exception output with reasons.
4. The clean output contains only records meeting the agreed validation criteria.
5. Raw values remain unchanged and source lineage is retained.
6. Reconciliation demonstrates how raw records are distributed across clean, exception and any explicitly excluded outcomes.
7. Re-running the same batch does not create duplicate clean records or unintended changes.
8. SQL scripts, rules, results and process documentation are committed to GitHub.

## Planned database objects

| Object | Purpose |
|---|---|
| `raw_policy_data` | Immutable source landing table |
| `stg_policy_data` | Standardised and validated working data |
| `clean_policy_data` | Approved reporting/migration output |
| `data_quality_exceptions` | Records and fields requiring investigation |
| `data_cleansing_rules` | Documented transformation and validation rules |
| `data_cleansing_decisions` | Business-approved resolutions |
| `pipeline_run_log` | Batch execution and processing outcomes |

The final schema may be refined as requirements and testing expose additional needs.

## Work completed

### Raw import and initial profiling

- Created the MySQL database and raw policy table.
- Imported the 100-row synthetic dataset into `raw_policy_data`.
- Confirmed 100 records were imported.
- Profiled source systems, source policy identifiers, broker and insured names, policy statuses, currencies and missing values.
- Identified 4 missing or blank written-premium values (4%).
- Profiled inception and expiry date patterns using regular expressions.
- Identified a free-text expiry value, `not supplied`, at source record 58.

### Initial technical observations

- 2 source systems.
- 99 distinct source policy identifiers across 100 rows.
- 10 distinct broker-name values.
- 16 distinct insured-name values.
- 6 distinct currency values.
- Policy status values include Active, Pending, Cancelled, Lapsed and Unknown.

A regular expression identifies a text pattern; it does not establish calendar validity. Date parsing and calendar validation will be treated as separate controls.

## Next steps

1. Complete profiling of premiums, commission, reporting year, country and potential duplicates.
2. Build the business questions and cleansing rules register.
3. Design the staging, clean and exception tables.
4. Implement transformations and validations incrementally.
5. Run, test, reconcile and document the complete pipeline.

## Repository structure

```text
04-insurance-data-cleansing/
├── README.md
├── data/
│   ├── raw/
│   └── data_dictionary.md
├── sql/
│   ├── 01_profile_raw_policy_data.sql
│   ├── 02_profile_premiums_and_commission.sql
│   ├── 03_validate_and_standardise_dates.sql
│   ├── 04_build_staging_layer.sql
│   ├── 05_validate_and_route_exceptions.sql
│   ├── 06_load_clean_policy_data.sql
│   ├── 07_reconcile_pipeline.sql
│   └── 08_run_pipeline.sql
├── documentation/
│   ├── business_rules_register.md
│   ├── cleansing_process.md
│   └── data_quality_findings.md
└── outputs/
    ├── profiling/
    └── exceptions/
```

Files will be added as the corresponding stages are built and tested.

## Skills demonstrated

MySQL, SQL development, CTEs, regular expressions, string manipulation, date parsing, data profiling, data modelling, ETL pipeline design, data validation, exception management, business-rule analysis, data lineage, reconciliation, batch processing and auditability.

## Status

**In progress — initial raw import and profiling completed.**

The next build stage is completing premium and commission profiling, while preparing the business rules and exception questions.
