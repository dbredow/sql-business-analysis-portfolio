# Project 04 — Data Model

## Purpose

This document describes the current logical relationships in the MySQL cleansing pipeline. It distinguishes implemented database objects from planned extensions.

## Entity relationship diagram

```mermaid
erDiagram
    RAW_POLICY_DATA ||--|| STAGING_POLICY_DATA : "copied to"
    RAW_POLICY_DATA ||--o{ DATA_VALIDATION_RESULTS : "validated as"
    PIPELINE_RUN_LOG ||--o{ DATA_VALIDATION_RESULTS : "records run"
    RAW_POLICY_DATA ||--o{ DATA_QUALITY_EXCEPTIONS : "raises"
    PIPELINE_RUN_LOG ||--o{ DATA_QUALITY_EXCEPTIONS : "raised during"
    RAW_POLICY_DATA ||--o| CLEAN_POLICY_DATA : "source for"

    RAW_POLICY_DATA {
        int RawRecordID PK
        varchar SourceSystem
        varchar SourcePolicyID
        varchar PolicyReference
        varchar WrittenPremiumRaw
        varchar CurrencyCodeRaw
        varchar ImportBatchID
        datetime ImportedAt
    }
    STAGING_POLICY_DATA {
        int RawRecordID PK,FK
        varchar WrittenPremiumRaw
        varchar CurrencyCodeRaw
        datetime LastProcessedAt
    }
    PIPELINE_RUN_LOG {
        int PipelineRunID PK
        datetime RunStartTime
        datetime RunCompleteTime
        varchar Outcome
        int RecordsProcessed
        int RecordsPassed
        int RecordsWithExceptions
    }
    DATA_VALIDATION_RESULTS {
        int ValidationResultID PK
        int PipelineRunID FK
        int RawRecordID FK
        varchar WrittenPremiumStatus
        datetime ValidatedAt
    }
    DATA_QUALITY_EXCEPTIONS {
        int ExceptionID PK
        int PipelineRunID FK
        int RawRecordID FK
        varchar FieldName
        varchar OriginalValue
        varchar ExceptionType
        varchar ExceptionStatus
        datetime RaisedAt
        datetime ResolvedAt
    }
    CLEAN_POLICY_DATA {
        int CleanRecordID PK
        int RawRecordID FK
        decimal WrittenPremium
        varchar CurrencyCode
        date InceptionDate
        date ExpiryDate
    }
```

The diagram is a relationship-level view. The physical tables contain additional policy attributes and validation-status columns.

## Grain and relationship rules

| Object | Grain | Purpose |
|---|---|---|
| `raw_policy_data` | One row per imported source record | Immutable source evidence |
| `Staging_Policy_Data` | One row per raw record | Working copy for processing |
| `pipeline_run_log` | One row per pipeline execution | Run-level audit and outcome |
| `data_validation_results` | One row per raw record per run | Wide snapshot of field validation statuses |
| `data_quality_exceptions` | One row per field-level exception per run | Investigation and resolution tracking |
| `clean_policy_data` | One row per fully cleansed policy | Final validated output |

## Key design decisions

- Raw source values are retained unchanged.
- Validation results are stored as a wide snapshot: one row per policy per pipeline run, with a separate status for each field.
- Validation status and exception management are separate concerns. A validation result records pass/fail; an exception records the issue requiring investigation.
- A policy may have multiple field-level exceptions, so exception counts must not be mistaken for distinct policy counts.
- The clean policy table is reserved for records that pass all required field and business-rule checks. Passing one field does not make the whole policy clean.
- Pipeline run records are at execution grain, not policy grain.

## Implementation status

Implemented: raw, staging, pipeline run log, validation results, exception register and final clean table.

Planned for a later stage: dedicated cleansing-rule and business-decision registers, plus any additional audit history required by the resolution workflow.
