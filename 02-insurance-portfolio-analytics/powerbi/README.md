# Power BI

## Purpose

Store the Power BI reports, dashboard designs and supporting documentation for the Insurance Portfolio Analytics project.

## Planned Deliverables

- Portfolio overview dashboard
- Premium and claims performance analysis
- Comparison of open market, third-party binders and in-house binders
- Group, department and business-level drill-down
- Class of business analysis
- Broker and handler performance
- Insurance market analysis
- Data-quality and reconciliation reporting

## Key Measures

Measures will be defined and validated before being implemented in Power BI.

Initial candidates include:

- Gross Written Premium (GWP)
- Earned Premium
- Incurred Claims
- Loss Ratio
- Policy and transaction counts
- Premium and claims movement over time

## Design Principles

- Reconcile report totals to the MySQL source data.
- Allow users to drill down from group to department to business.
- Compare product channels using consistent definitions.
- Avoid double-counting premiums or claims.
- Clearly document measure definitions and assumptions.
- Use synthetic data only.

## Status

Initial project setup. Dashboard development will begin after the underlying data model, SQL queries and validation checks have been established.
