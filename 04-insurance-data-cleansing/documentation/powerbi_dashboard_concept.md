# Project 04 — Power BI Dashboard Concept

## Purpose

The Power BI dashboard will provide an operational and management view of the Insurance Data Cleansing Pipeline. It will show how the 100 source records progress through field-level validation, exception investigation and final whole-policy release.

This document describes a proposed dashboard design. It is a design concept, not a live Power BI report. The dashboard will be built after the SQL reporting views are available.

## Design principles

- Use MySQL as the system of record and SQL views as the reporting layer.
- Keep the dashboard read-only: corrections and exception decisions remain controlled SQL/business processes.
- Clearly distinguish field-level validation from whole-policy cleanliness.
- Show outstanding and resolved exceptions separately.
- Provide drill-through from summary metrics to the affected records.
- Display the pipeline run and refresh timestamp so users know which run they are viewing.
- Reconcile all displayed totals to the SQL views.

## Proposed report navigation

| Page | Audience / question | Main content |
|---|---|---|
| 1. Executive Overview | How is the cleansing exercise progressing? | KPI cards, progress, outstanding issues, run status |
| 2. Field Validation | Which fields are passing or failing? | Field-by-field valid, exception and pending counts |
| 3. Exception Management | What needs investigation or approval? | Outstanding/resolved trend, exception types and detail |
| 4. Reconciliation | Can every source record be accounted for? | Raw, staging, field validation, whole-policy and clean counts |
| 5. Pipeline & Audit | What happened in each processing run? | Run history, duration, outcome and exception movements |

## Page 1 — Executive Overview (wireframe)

The following is a conceptual layout. Figures shown are the current Written Premium field results only, not whole-policy cleanliness.

| KPI card | Illustrative current value | Definition |
|---|---:|---|
| Source records | 100 | Records imported into the source batch |
| Written Premium valid | 94 | Records passing the current Written Premium rule |
| Written Premium outstanding | 6 | Records still failing Written Premium validation |
| Written Premium validation rate | 94% | 94 valid / 100 assessed |

Suggested visual layout:

```text
+------------------------------------------------------------------+
| INSURANCE DATA CLEANSING                         Run: 1 | Refresh |
+------------------+------------------+----------------+------------+
| Source records   | Premium valid    | Outstanding    | Pass rate  |
|       100        |       94         |       6        |    94%     |
+------------------+------------------+----------------+------------+
|                                                                  |
| Field validation progress                                        |
| Written Premium  [##############################------] 94%     |
| CurrencyCode     [                  Pending                  ]  |
| CommissionPct    [                  Pending                  ]  |
| Dates             [                  Pending                  ]  |
| Country           [                  Pending                  ]  |
|                                                                  |
+--------------------------------+---------------------------------+
| Outstanding exceptions        | Pipeline run status             |
| Blank values             2    | Run outcome / start / finish     |
| TBC placeholders         2    | Records processed                |
| Whitespace               2    | Last refresh timestamp           |
+--------------------------------+---------------------------------+
```

The progress bars for fields not yet processed should show Pending / Not started, not 0% valid. A 0% result would imply the field had been assessed and no records passed.

## Page 2 — Field Validation

Recommended visuals:
- Matrix with field name as rows and Valid, Exception, Pending counts as values.
- Bar chart showing validation rate for fields that have actually been assessed.
- Slicers for pipeline run and source system.
- Drill-through to record-level validation detail.

Suggested measures (final DAX depends on the SQL view grain and column names):

- Valid records by field.
- Exception records by field.
- Pending records by field.
- Validation rate = Valid / (Valid + Exception), excluding Pending.
- Assessed records = Valid + Exception.

Do not average field-level validation percentages to derive a whole-policy quality score.

## Page 3 — Exception Management

Recommended visuals:
- KPI cards: Outstanding, Resolved and Closed.
- Stacked bar chart by field and exception type.
- Detail table with source record, field, original value, reason, status, raised date, resolution date and notes.
- Filters for source system, field, exception status and pipeline run.

Current Written Premium exception position:
- 17 original formatting exceptions have been resolved after successful revalidation.
- 6 remain outstanding: two blank values, two `TBC` placeholders and two whitespace-only values.

Resolved exceptions should remain visible for audit purposes; they should not disappear from the report.

## Page 4 — Reconciliation

This page must distinguish two levels of reconciliation.

**Field-level reconciliation**

For Written Premium at the current stage:

`100 assessed = 94 Valid + 6 Exception`

**Whole-policy reconciliation**

This should only be calculated after every required field has been assessed. Each policy should then be classified as fully clean or not yet clean / carrying one or more outstanding exceptions.

Recommended visuals:
- Source-to-staging record count comparison.
- Field-level status reconciliation.
- Whole-policy status cards and trend.
- Clean output versus not-yet-clean records.
- Reconciliation exception indicator.

Avoid summing exception rows to calculate the number of affected policies: one policy may have multiple field-level exceptions. Use distinct policy/source-record counts for whole-policy measures.

## Page 5 — Pipeline & Audit

Recommended visuals:
- Pipeline run history table.
- Run outcome, start time, completion time and duration.
- Records processed, passed and with exceptions.
- Exceptions raised and resolved by run.
- Refresh timestamp and selected run identifier.

## Proposed SQL reporting layer

The following views are proposed and will be confirmed against the actual schema before development:

| Proposed view | Dashboard use |
|---|---|
| `vw_pipeline_run_summary` | Executive overview and run history |
| `vw_field_validation_summary` | Field validation matrix and progress |
| `vw_exception_summary` | Exception status and category visuals |
| `vw_exception_detail` | Exception drill-through |
| `vw_policy_quality_status` | Whole-policy clean / not-clean classification |
| `vw_reconciliation_summary` | Source, staging and clean reconciliation |

## Refresh and control approach

1. SQL processing updates staging, validation and exception records.
2. SQL views expose the latest agreed reporting grain.
3. Power BI refreshes from those views.
4. Dashboard totals are checked against direct SQL reconciliation queries.
5. The report displays the pipeline run identifier and last refresh timestamp.

For the initial build, a manual refresh is sufficient. Refresh scheduling and gateway configuration can be considered once the report and MySQL environment are stable.

## Future enhancements

- Source-system comparison and data-quality trends.
- Exception ageing and resolution turnaround.
- Field-level rule catalogue and business approval status.
- Pipeline run-to-run comparison.
- Data-quality scorecards by source system.
- Whole-policy release monitoring.

## Important caveat

The current 94% figure is the Written Premium field validation rate only. It must not be presented as 94% of policies being fully cleansed. Whole-policy cleanliness will be measured only after all required fields have been validated.
