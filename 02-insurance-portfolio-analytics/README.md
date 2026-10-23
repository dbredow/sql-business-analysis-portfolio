# Project 02 — Insurance Portfolio Analytics

## 1. Project Overview

This project will develop a SQL-driven insurance portfolio reporting solution using **MySQL and Power BI**.

The objective is to combine premium and claims data across different insurance business channels and produce management reporting at portfolio, group, department and individual business levels.

The project will demonstrate business analysis, relational data modelling, cross-database SQL, financial reporting, data validation and business intelligence.

All data will be synthetic and created for learning and portfolio demonstration.

## 2. Business Objectives

The solution aims to answer the following questions:

- What are the total earned premium, incurred claims and loss ratio for the overall portfolio?
- How do individual groups and departments contribute to portfolio performance?
- Which individual businesses are driving premium and claims results?
- How does performance differ across open-market, third-party binder and in-house binder business?
- How do results change over monthly, quarterly and annual reporting periods?
- Can financial results be reconciled to the underlying source data?
- Are there missing mappings, unmatched records or potential duplicate transactions?

## 3. Business Scope

### 3.1 Product Channels

The initial model will include:

- Open-market business
- Third-party binders
- In-house binders

### 3.2 Business Dimensions

The reporting model will consider:

- Group
- Department
- Individual business
- Class of business
- Broker
- Handler
- Insurance market, including Lloyd's and company markets
- Reporting period

These dimensions will be refined during the requirements and data-modelling stages.

## 4. Proposed Technical Architecture

### MySQL

MySQL will provide the source databases, data integration, SQL calculations and validation logic.

The initial learning design will explore separate databases for:

- Open-market premium transactions
- Third-party binder premium transactions
- In-house binder premium transactions
- Claims data
- Shared business and reference data

The databases will initially reside on the same MySQL server so that cross-database queries can be practised using fully qualified table names.

This is a proposed training architecture and may be refined as the requirements develop.

### Power BI

Power BI will provide the management reporting and visualisation layer.

The planned dashboard will support:

- Overall portfolio reporting
- Group-level analysis
- Department-level analysis
- Business-level drill-down
- Product-channel comparisons
- Class, broker and market analysis
- Monthly, quarterly and annual trends
- Data-quality and reconciliation reporting

## 5. Key Financial Measures

### Earned Premium

Premium attributable to insurance cover provided during the relevant reporting period, based on the agreed business definition.

### Incurred Claims

Claims cost recognised under the agreed reporting basis, including the appropriate treatment of payments, outstanding reserves, recoveries and adjustments.

### Loss Ratio

Loss ratio will be calculated as:

**Loss Ratio = Total Incurred Claims / Total Earned Premium × 100%**

Ratios will be calculated from aggregated financial amounts rather than by averaging individual business or monthly loss ratios.

The detailed calculation rules will be documented before the reporting SQL is developed.

## 6. Project Delivery Plan

The project will be delivered through smaller, independently understandable stages.

| Stage | Focus | Intended outcome |
|---|---|---|
| 02A | Cross-database SQL | Understand and practise joins across MySQL databases |
| 02B | Business requirements and data model | Define entities, relationships and reporting dimensions |
| 02C | Premium data | Create and integrate synthetic premium transactions |
| 02D | Claims data | Model claims records and financial movements |
| 02E | Financial reporting | Calculate portfolio, group, department and business results |
| 02F | Data validation | Test data quality and reconcile financial totals |
| 02G | Power BI | Develop the management dashboard |
| 02H | Project completion | Document the solution and publish supporting evidence |

The order may be adjusted as individual requirements and dependencies become clearer.

## 7. Data Quality and Validation

Validation will be incorporated throughout the project.

Planned controls include:

- Duplicate transaction detection
- Missing business and group mappings
- Unmatched premium and claims records
- Source-to-reporting financial reconciliation
- Reporting-period consistency
- Validation of financial aggregations and loss-ratio calculations

Exceptions will be identified and explained rather than silently excluded from reporting.

## 8. Design Principles

The project will follow these principles:

1. Start with business reporting requirements and work backwards to the required data inputs.
2. Keep each learning stage small and manageable.
3. Define table grain and join keys before combining financial data.
4. Avoid double-counting premiums and claims.
5. Keep business channel, organisational hierarchy and insurance market as distinct concepts.
6. Make financial calculations traceable to source records.
7. Document assumptions and unresolved decisions.
8. Validate results before presenting them in Power BI.
9. Use synthetic data throughout.

## 9. Definition of Success

The project will be considered complete when it contains:

- Documented business requirements and assumptions
- A clear data model and architecture
- Reproducible MySQL database creation and sample-data scripts
- Cross-database SQL examples
- Validated portfolio and business-level financial reporting
- Data-quality and reconciliation tests
- A Power BI dashboard with hierarchy drill-down
- Documentation sufficient for another person to understand and reproduce the solution

## 10. Project Status

**Current status:** Initial project definition.

**Next milestone:** Establish the requirements and create a small cross-database SQL exercise in MySQL.

The project will develop incrementally, with decisions, scripts, tests and supporting documentation maintained in this repository.

