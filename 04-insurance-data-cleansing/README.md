# Project 04 — Insurance Data Cleansing Pipeline

## Project overview

Build a repeatable, auditable SQL data-cleansing pipeline for insurance policy data received from multiple source systems, with a Power BI dashboard to monitor data quality, exceptions and reconciliation.

The project uses a 100-row synthetic policy dataset containing deliberately inconsistent, incomplete and potentially invalid values. The objective is to transform raw inputs into validated, reporting- or migration-ready outputs without losing source evidence or silently inventing business answers.

This is an end-to-end business and data project covering data profiling, database design, validation, exception management, controlled resolution, reconciliation, auditability and data-quality reporting.

All dataset records are synthetic.

## Business objectives

- Understand the quality and structure of incoming policy data.
- Identify completeness, validity, consistency and uniqueness issues.
- Define repeatable technical rules and identify where business approval is required.
- Preserve original source values and maintain lineage.
- Route invalid or ambiguous values into an auditable exception workflow.
- Release only fully validated policy records to the final clean output.
- Reconcile records and retain evidence of each pipeline run.
- Present data-quality progress and control outcomes through Power BI.

## Dataset

The initial dataset contains 100 synthetic policy records from two source systems. Fields include source identifiers, policy references, broker and insured names, policy status, inception and expiry dates, written premium, currency, commission percentage, reporting year, country and import metadata.

The data deliberately includes inconsistent formats, mixed case and spacing, missing values, free-text entries and values requiring validation.

## Solution architecture

`raw_policy_data` → `Staging_Policy_Data` → validation and exception management → `clean_policy_data`

Supporting controls include `pipeline_run_log` and `data_validation_results`. SQL reporting views will provide the Power BI reporting layer.

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
- Resolved exceptions remain in the register as audit history.

### 4. Final clean output

- `clean_policy_data` is reserved for complete policy records that satisfy all required validation rules.
- Passing one field does not make an entire policy clean.
- Source lineage is retained through the source record key.

### 5. Run control, reconciliation and reporting

- `pipeline_run_log` records one row per pipeline execution.
- Field-level and whole-policy reconciliation are reported separately.
- Reruns must be controlled so they do not create duplicates or damage prior audit evidence.
- Power BI will consume purpose-built SQL views and refresh as the underlying pipeline progresses.

## Data model and process documentation

- [Data model and ERD](./documentation/data_model.md)
- [Cleansing process map](./documentation/cleansing_process.md)
- [Use Case 01 — Written Premium validation](./documentation/use_case_01_written_premium.md)
- [Development plan and delivery roadmap](./documentation/development_plan.md)
- [Power BI reporting](./documentation/powerbi_reporting.md)

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

The initial exceptions included comma thousands separators, erroneous `Â£` symbol/encoding artefacts, blank values, whitespace-only values and `TBC` placeholders.

### Current Written Premium position

After applying the agreed formatting treatments in staging and rerunning validation:

| Current field status | Records | Share |
|---|---:|---:|
| Valid | 94 | 94% |
| Exception | 6 | 6% |
| **Total** | **100** | **100%** |

Of the original 23 exception records:
- 17 were standardised in staging, passed revalidation and were marked Resolved in the exception register.
- 6 remain Outstanding: two blank values, two `TBC` placeholders and two whitespace-only values.

The six outstanding records have not been replaced with zero or another assumed premium. Any such treatment requires an explicit business decision and supporting approval.

This is a **Written Premium field-level result only**. It does not mean 94 policies are fully cleansed or ready for the final clean table. Other required fields must pass validation before a policy can be released as clean.

## Design principles and governance

- **Preserve evidence:** never overwrite the raw source values.
- **Process incrementally:** validate one field at a time, with an explicit rule and measurable outcome.
- **Do not guess:** ambiguous values remain exceptions until evidence and an approved decision support resolution.
- **Keep audit history:** record run outcomes, validation statuses and exception decisions.
- **Use the right grain:** a validation snapshot is one record per policy per run; an exception is one record per failed field per policy per run.
- **Release complete records only:** the final clean table contains policies that have passed all required checks.
- **Reconcile explicitly:** distinguish field-level outcomes from whole-policy outcomes.
- **Report honestly:** dashboard measures must distinguish field-level validation from whole-policy cleanliness.

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
| SQL reporting views | Power BI reporting layer | Planned |
| `data_cleansing_rules` | Formal rules register | Planned |
| `data_cleansing_decisions` | Business-approved decisions and resolutions | Planned |

## Current progress

### Completed

- Created the MySQL database and raw policy table.
- Imported and confirmed 100 synthetic policy records from two source systems.
- Created the staging table and loaded 100 working records.
- Created the pipeline run log and initiated the first run.
- Created the wide validation-results table with one row per source record per run.
- Created the field-level exception register.
- Created the final clean policy table with data integrity constraints.
- Completed initial profiling of Written Premium.
- Agreed and applied the Written Premium formatting treatments in staging: removed thousands separators and the erroneous `Â£` symbol/encoding artefact.
- Revalidated all 100 Written Premium values: 94 Valid and 6 Exception.
- Resolved 17 formatting exceptions after successful revalidation.
- Confirmed 6 outstanding Written Premium exceptions: two blank, two `TBC`, two whitespace-only.
- Saved and labelled the SQL scripts documenting the execution sequence.

### Current stage

**Written Premium — 94 Valid, 6 Outstanding exceptions.** The six outstanding records require investigation and a business decision; no replacement value has been assumed.

### Next stages

1. Profile CurrencyCode, including whitespace, case, recognised ISO currency codes and unknown/placeholder values.
2. Agree CurrencyCode cleansing and validation rules, distinguishing deterministic formatting from business decisions.
3. Clean CurrencyCode in staging, revalidate and reconcile its exception register.
4. Continue field-by-field through commission percentage, dates, reporting year, country and other required fields.
5. Investigate the six outstanding Written Premium exceptions and record any approved business decision.
6. Create SQL reporting views for pipeline progress, field validation, exception management and reconciliation.
7. Connect Power BI to the MySQL reporting views and build the dashboard iteratively.
8. Load fully validated policies to the final clean table.
9. Complete whole-policy reconciliation, rerun testing and end-to-end QA.

## Power BI dashboard

The proposed Power BI dashboard is documented in [Power BI Reporting](./documentation/powerbi_reporting.md). It will include:
- Executive overview of records processed, field-level quality and outstanding exceptions.
- Field-by-field validation progress.
- Exception analysis and resolution history.
- Source-to-staging-to-clean reconciliation.
- Pipeline run and audit monitoring.

The dashboard is a planned reporting layer. It is not yet connected to MySQL, and the current Written Premium figures above are manually verified project results rather than live Power BI measures.

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
9. Power BI measures reconcile to the SQL reporting layer and clearly distinguish field-level from whole-policy status.

## Skills and technologies

MySQL, SQL development, regular expressions, string manipulation, data profiling, relational data modelling, ETL pipeline design, data validation, exception management, business-rule analysis, data lineage, reconciliation, batch processing, auditability, Power BI data modelling and dashboard design.

## Repository structure

```text
04-insurance-data-cleansing/
├── README.md
├── data/
├── sql/
└── documentation/
    ├── data_model.md
    ├── cleansing_process.md
    ├── use_case_01_written_premium.md
    ├── development_plan.md
    └── powerbi_dashboard_concept.md
```
