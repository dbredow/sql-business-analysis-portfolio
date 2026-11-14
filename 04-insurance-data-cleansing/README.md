# Project 04 — Insurance Data Cleansing Pipeline

## Project overview

Build a repeatable, auditable SQL data-cleansing pipeline for insurance policy data received from multiple source systems.

The project uses a 100-row synthetic policy dataset containing deliberately inconsistent, incomplete and potentially invalid values. The objective is to transform raw inputs into validated, reporting- or migration-ready outputs without losing source evidence or silently inventing business answers.

This is an end-to-end business and data project covering data profiling, database design, validation, exception management, controlled resolution, reconciliation and auditability.

All dataset records are synthetic.

## Business objectives

- Understand the quality and structure of incoming policy data.
- Identify completeness, validity, consistency and uniqueness issues.
- Define repeatable technical rules and identify where business approval is required.
- Preserve original source values and maintain lineage.
- Route invalid or ambiguous values into an auditable exception workflow.
- Release only fully validated policy records to the final clean output.
- Reconcile records and retain evidence of each pipeline run.

## Dataset

The initial dataset contains 100 synthetic policy records from two source systems. Fields include source identifiers, policy references, broker and insured names, policy status, inception and expiry dates, written premium, currency, commission percentage, reporting year, country and import metadata.

The data deliberately includes inconsistent formats, mixed case and spacing, missing values, free-text entries and values requiring validation.

## Solution architecture

`raw_policy_data` → `Staging_Policy_Data` → validation and exception management → `clean_policy_data`

Supporting controls include `pipeline_run_log` and `data_validation_results`.

### 1. Raw data

- Preserves source values as received.
- Retains source identifiers and import metadata.
- Is treated as immutable evidence; transformations do not overwrite raw values.

### 2. Staging

- Provides the working copy for profiling, standardisation and validation.
- Retains raw field values for comparison and traceability.
- Supports incremental, one-field-at-a-time processing.

### 3. Validation and exceptions

- `data_validation_results` records field-level status for each source record and pipeline run.
- `data_quality_exceptions` records the fields requiring investigation, including original values and exception reasons.
- Validation outcomes and exception investigation are separate concerns.
- Business decisions are required where a value cannot safely be inferred.

### 4. Final clean output

- `clean_policy_data` is reserved for complete policy records that satisfy all required validation rules.
- Passing one field does not make an entire policy clean.
- Source lineage is retained through the source record key.

### 5. Run control and reconciliation

- `pipeline_run_log` records one row per pipeline execution.
- Field-level and whole-policy reconciliation are reported separately.
- Reruns must be controlled so they do not create duplicates or damage prior audit evidence.

## Data model and process documentation

- [Data model and ERD](./documentation/data_model.md)
- [Cleansing process map](./documentation/cleansing_process.md)
- [Use Case 01 — Written Premium validation](./documentation/use_case_01_written_premium.md)

The ERD describes the current logical relationships and distinguishes implemented objects from planned extensions. The process map shows the end-to-end workflow, including exception investigation, business decisions, revalidation and final release.

## First use case — Written Premium

The first validation cycle focuses exclusively on the Written Premium field.

Agreed format rule:

```regex
^[0-9]+([.][0-9]{2})?$
```

The initial profile of 100 records identified:

| Written Premium profile | Records | Share |
|---|---:|---:|
| Matches agreed numeric format | 77 | 77% |
| Does not match agreed numeric format | 23 | 23% |
| **Total** | **100** | **100%** |

Field-level profiling reconciliation:

`100 = 77 + 23`

This is a field-level result, not a claim that 77 complete policies are ready for the final clean table. Other required fields must pass validation before a policy can be released as clean.

The detailed use case records the rule, profiling observations, audit treatment and next steps. The 77/23 figures are identified as profiling results; post-execution routing counts are to be verified separately after the validation script is run.

## Design principles and governance

- **Preserve evidence:** never overwrite the raw source values.
- **Process incrementally:** validate one field at a time, with an explicit rule and measurable outcome.
- **Do not guess:** ambiguous values remain exceptions until evidence and an approved decision support resolution.
- **Keep audit history:** record run outcomes, validation statuses and exception decisions.
- **Use the right grain:** a validation snapshot is one record per policy per run; an exception is one record per failed field per policy per run.
- **Release complete records only:** the final clean table contains policies that have passed all required checks.
- **Reconcile explicitly:** distinguish field-level outcomes from whole-policy outcomes.

Examples of deterministic technical treatments include trimming whitespace or uppercasing a recognised currency code. Replacing a missing currency, interpreting an ambiguous date or correcting a premium may require business confirmation.

## Database objects

| Object | Purpose | Status |
|---|---|---|
| `raw_policy_data` | Immutable source landing table | Implemented |
| `Staging_Policy_Data` | Working copy for processing | Implemented |
| `data_validation_results` | Wide field-status snapshot per record per run | Implemented |
| `data_quality_exceptions` | Field-level exception register | Implemented |
| `pipeline_run_log` | Pipeline execution and outcome log | Implemented |
| `clean_policy_data` | Final fully validated policy output | Table created; loading follows complete validation |
| `data_cleansing_rules` | Formal rules register | Planned |
| `data_cleansing_decisions` | Business-approved decisions and resolutions | Planned |

## Current progress

### Completed

- Created the MySQL database and raw policy table.
- Imported and confirmed 100 synthetic policy records.
- Created the staging table and loaded 100 working records.
- Created the pipeline run log and initiated the first run.
- Created the wide validation-results table with one row per source record per run.
- Created the field-level exception register.
- Created the final clean policy table with data integrity constraints.
- Completed initial profiling of Written Premium.
- Agreed the Written Premium format rule and identified 77 format-valid and 23 format-exception candidates.
- Documented the initial data model, process map and first use case.

### Current stage

**Written Premium — initial profiling completed; validation routing and exception investigation are the next execution steps.**

The first use case will be closed only after the validation statuses and exception records have been written and reconciled against all 100 source records. The 23 exceptions will then be investigated and resolved using evidence and approved rules.

### Next stages

1. Execute and verify Written Premium validation and exception routing.
2. Investigate, resolve and revalidate the 23 Written Premium exceptions.
3. Document the completed first use case and update the profiling evidence.
4. Move to the next field only after the Written Premium cycle is reviewed.
5. Continue field-by-field until all required policy fields pass.
6. Load fully validated policies to the final clean table.
7. Complete whole-policy reconciliation, rerun testing and end-to-end QA.

## Acceptance criteria

The project will be considered complete when:

1. All 100 source records are accounted for by the pipeline.
2. Each transformation is supported by a documented technical rule or business-approved decision.
3. Invalid and unresolved field values are routed to exceptions with original values and reasons.
4. The final clean output contains only policies meeting all required validation criteria.
5. Raw values remain unchanged and source lineage is retained.
6. Field-level and whole-policy reconciliations are evidenced at the correct grain.
7. Rerunning a batch does not create duplicate clean records or unintended changes.
8. SQL scripts, rules, results and process documentation are committed to GitHub.

## Skills and technologies

MySQL, SQL development, regular expressions, string manipulation, data profiling, relational data modelling, ETL pipeline design, data validation, exception management, business-rule analysis, data lineage, reconciliation, batch processing and auditability.

## Repository structure

```text
04-insurance-data-cleansing/
├── README.md
├── data/
├── sql/
└── documentation/
    ├── data_model.md
    ├── cleansing_process.md
    └── use_case_01_written_premium.md
```

SQL scripts, source data and evidence outputs will be added as the corresponding stages are completed and verified.
