# Use Case 01 — Written Premium Validation

## Objective

Demonstrate the first field-level validation cycle using the Written Premium source value. The objective is to distinguish values that match the agreed numeric format from values requiring investigation, while preserving the original source value.

## Scope

This use case processes Written Premium only. Currency, commission, dates and other policy fields are deliberately outside this first validation cycle.

Dataset: 100 synthetic policy records.

## Agreed validation rule

Accepted format:

```regex
^[0-9]+([.][0-9]{2})?$
```

Interpretation:

- One or more digits are required.
- An optional decimal component may contain a decimal point followed by exactly two digits.
- The entire value must match the pattern.
- Whole-number values are accepted and can be represented as two-decimal-place values in a numeric target column.
- Negative values, thousands separators, currency symbols, alphabetic text, blank values and malformed decimal precision do not pass this format rule.

This is a format check, not a business validation of whether a premium amount is commercially correct.

## Initial profiling result

| Outcome | Records | Share |
|---|---:|---:|
| Matches agreed format | 77 | 77% |
| Does not match agreed format | 23 | 23% |
| **Total** | **100** | **100%** |

The initial diagnostic profile identified examples of comma separators, currency-symbol/encoding artefacts, alphabetic content, empty strings and whitespace-only values. Diagnostic categories can overlap; they should not be added together as if they were mutually exclusive record counts.

## Cleansing treatments applied

The following deterministic formatting treatments were applied to the staging copy only:

- Removed thousands-separator commas from eligible Written Premium values.
- Removed the erroneous `Â£` symbol/encoding artefact from eligible Written Premium values.
- Kept the raw source table unchanged.
- Did not infer or change CurrencyCode as part of Written Premium cleansing.

These treatments standardised the text representation. They did not establish whether a premium amount was commercially correct or whether the associated currency was correct.

## Current validation and exception outcome

After the staging treatments, the Written Premium validation rule was rerun for all 100 records.

| Current outcome | Records | Share |
|---|---:|---:|
| Valid | 94 | 94% |
| Exception | 6 | 6% |
| **Total** | **100** | **100%** |

Of the original 23 exceptions:
- 17 formatting exceptions passed revalidation and were marked Resolved in the exception register.
- 6 remain Outstanding.

The six outstanding records are:

| RawRecordID | Original value | Observed issue |
|---:|---|---|
| 18 | Blank | Missing value |
| 24 | `TBC` | Placeholder requiring confirmation |
| 31 | Whitespace | Whitespace-only value |
| 67 | Blank | Missing value |
| 85 | `TBC` | Placeholder requiring confirmation |
| 94 | Whitespace | Whitespace-only value |

The six records remain exceptions. No zero value or other replacement premium has been assumed. Any replacement requires an explicit business decision and supporting approval.

## Reconciliation

Initial profiling:

`100 = 77 initially format-valid + 23 initially format-exception`

After staging standardisation and revalidation:

`100 = 94 Valid + 6 Exception`

Exception movement:

`23 original exceptions = 17 resolved after revalidation + 6 outstanding`

These are field-level Written Premium results. They do not mean that 94 complete policies are ready for the final clean table. A policy enters `clean_policy_data` only after all required fields and business rules pass.

## Processing and audit treatment

- Every source record receives a Written Premium status in `data_validation_results` for the pipeline run.
- Values matching the agreed expression are marked `Valid`.
- Values not matching the expression are marked `Exception`.
- Failed field values are represented in `data_quality_exceptions`, retaining the original value and exception reason.
- The 17 formatting exceptions were marked Resolved only after their updated staging values passed revalidation.
- The six unresolved values remain Outstanding for investigation.
- Raw source values remain unchanged.
- Validation status and exception resolution are separate controls.

## Next steps

1. Investigate the six outstanding Written Premium values and obtain business evidence or an approved disposition.
2. Profile CurrencyCode as the next field, treating currency code as separate from premium text formatting.
3. Agree CurrencyCode standardisation and validation rules before applying transformations.
4. Continue the field-by-field validation process.
5. Only after all required fields pass, classify whole policies and load eligible records into the final clean table.
