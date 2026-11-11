# Project 04 — Insurance Data Cleansing & Standardisation

## Overview
A practical data-quality project using a 100-row synthetic insurance policy dataset from two source systems. The objective is to profile incoming data, identify quality issues, apply transparent standardisation rules, separate exceptions and produce validated reporting- or migration-ready outputs.

## Business objectives
- Profile completeness, uniqueness, validity and consistency.
- Identify differences between source-system conventions.
- Preserve original source values.
- Standardise values only where the transformation is supported by an explicit rule.
- Route unresolved values to exceptions.
- Reconcile raw records to valid outputs and exceptions.

## Dataset
The initial dataset contains 100 synthetic policy records from two source systems. It includes source identifiers, policy references, broker and insured names, policy status, raw inception and expiry dates, written premium, currency, commission percentage, reporting year, country and import metadata.

The data deliberately includes inconsistent formats, mixed case and spacing, missing values, free-text entries and values requiring validation. All records are synthetic.

## Work completed — 11 November 2026

### Raw import
- Created the MySQL database and raw policy table.
- Imported the 100-row dataset into raw_policy_data.
- Confirmed 100 records were imported.

### Initial profiling
Built SQL checks for source systems, source policy identifiers, broker and insured names, policy status, currencies, and NULL, empty-string and whitespace-only values.

Initial observations:
- 2 source systems.
- 99 distinct source policy identifiers across 100 rows.
- 10 distinct broker-name values.
- 16 distinct insured-name values.
- 6 distinct currency values.
- 4 missing or blank written-premium values (4%).
- Status values include Active, Pending, Cancelled, Lapsed and Unknown.

### Date profiling
Used regular expressions to classify common date shapes:
- YYYY-MM-DD
- DD-MM-YYYY
- DD-Mon-YYYY
- YYYY/MM/DD
- DD/MM/YYYY
- DD/Mon/YYYY

One expiry value containing free text was isolated: not supplied (source record 58).

A regular expression recognises a text pattern; it does not prove that a value is a valid calendar date. Date parsing and calendar validation are separate steps.

## Data-quality principles
- Never overwrite the raw source layer.
- Distinguish NULL, empty and whitespace-only values.
- Do not infer missing business information.
- Do not guess ambiguous dates.
- Keep transformations explicit and repeatable.
- Record exception reasons for investigation.

## Planned work

### Phase 1 — Complete profiling
- Profile premium formats, including commas, currency symbols, non-numeric values and zero values.
- Profile commission percentage representations.
- Profile reporting years and country values.
- Investigate duplicate source identifiers and policy references.
- Summarise findings in a data-quality profile.

### Phase 2 — Date validation
- Convert recognised formats using explicit STR_TO_DATE format masks.
- Validate calendar dates, not just text patterns.
- Identify impossible and ambiguous dates.
- Use source-specific interpretation only where supported by evidence.
- Route free text and unresolved values to exceptions.

### Phase 3 — Standardisation
- Trim and standardise broker and insured names while preserving raw values.
- Standardise statuses and currency codes using controlled mappings.
- Convert premiums and commission percentages to numeric representations.
- Validate reporting years and country values.
- Document each transformation and business rule.

### Phase 4 — Staging and exceptions
- Create a standardised staging layer.
- Apply field-level and record-level validation.
- Separate valid records from exceptions.
- Capture exception reasons for investigation and resolution.

### Phase 5 — Clean output and reconciliation
- Produce a clean policy dataset for reporting or migration.
- Reconcile raw records to valid records and exceptions.
- Demonstrate before-and-after examples.
- Complete the data dictionary and process documentation.

## Proposed pipeline
raw_policy_data → stg_policy_data → validation → clean_policy_data

Failed records will be reported separately as exceptions. The raw source layer remains unchanged.

## Planned repository structure
- README.md
- data/raw/ — original synthetic source dataset
- data/data_dictionary.md
- sql/01_profile_raw_policy_data.sql
- sql/02_validate_raw_dates.sql
- sql/03_profile_premiums_and_commission.sql
- sql/04_standardise_policy_data.sql
- sql/05_validate_staged_data.sql
- sql/06_reconciliation.sql
- outputs/profiling/
- outputs/exceptions/
- documentation/cleansing_process.md

## Skills demonstrated
MySQL, SQL, data profiling, data-quality assessment, NULL handling, regular expressions, date parsing, data standardisation, exception management, reconciliation, business-rule analysis and controlled data migration.

## Status
In progress — initial profiling completed. Next: premium and commission profiling, followed by date conversion and calendar validation.
