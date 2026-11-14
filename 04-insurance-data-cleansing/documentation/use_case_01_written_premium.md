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

## Reconciliation

`100 = 77 + 23`

This is the first field-level profiling reconciliation: all 100 records are classified for the Written Premium field.

## Processing and audit treatment

For the validation run:

- Every source record receives a Written Premium status in `data_validation_results`.
- Values matching the agreed expression are marked `Valid`.
- Values not matching the expression are marked `Exception`.
- Each failed field is represented in `data_quality_exceptions`, retaining its original value and exception reason.
- Raw source values remain unchanged.
- The 77 format-valid values are not, by themselves, 77 fully cleansed policies. A policy enters `clean_policy_data` only after all required fields and business rules pass.

## Status and evidence

The 77/23 figures above are the initial profiling outcome. The execution status of the routing script and its post-run database reconciliation must be recorded separately after that script has been run and its results checked.

## Next steps

1. Execute the Written Premium validation and exception-routing script.
2. Verify 77 `Valid` and 23 `Exception` statuses for the run.
3. Verify that 23 Written Premium exception records were created, with no unintended exceptions for other fields.
4. Investigate and resolve the Written Premium exceptions using evidence and approved business rules.
5. Revalidate Written Premium before moving to the next field.
