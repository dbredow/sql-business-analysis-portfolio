# Testing and Data Validation

## Purpose

Document the testing approach used to validate the Insurance Portfolio Analytics project.

Testing will confirm that SQL queries produce accurate, consistent and explainable results.

## Planned Tests

### 1. Database Connectivity
- Confirm that the required MySQL databases exist.
- Confirm that the user has the required permissions.
- Confirm that tables can be queried across databases on the same MySQL server.

### 2. Data Integrity
- Identify missing or duplicate business keys.
- Check mandatory fields for NULL values.
- Validate foreign-key relationships and reference data.
- Check dates, currencies and numeric values.

### 3. Join Validation
- Confirm the expected grain of each table.
- Validate join keys and relationship cardinality.
- Check whether joins unexpectedly increase row counts.
- Confirm that premium and claims totals are not duplicated.

### 4. Financial Reconciliation
- Reconcile SQL reporting totals to source-table totals.
- Validate premium and claims aggregation.
- Check loss-ratio calculations against independently calculated examples.
- Investigate differences and document their causes.

### 5. Reporting Validation
- Compare results at business, department and group levels.
- Confirm that lower-level totals reconcile to higher-level totals where the business rules require this.
- Validate filters for reporting period, product channel, class and market.

## Testing Principles

- Use synthetic data with known expected results.
- Include normal cases, edge cases and deliberately incorrect records.
- Record expected results and actual results.
- Investigate failures rather than adjusting expected results to make a test pass.
- Do not publish financial measures until they have been validated.

## Status

Initial project setup. Test cases will be added as each part of the solution is developed.
