# Data Model

## Purpose

Document the database architecture, entities, relationships and data grain required for the Insurance Portfolio Analytics project.

## Planned contents

- Database architecture and cross-database relationships
- Premium transaction data
- Claims and claims financial data
- Product channels
- Groups, departments and individual businesses
- Classes of business
- Brokers and handlers
- Insurance markets
- Entity relationship diagram (ERD)
- Primary keys, foreign keys and business identifiers
- Data grain and join cardinality

## Design Principles

- Define the grain of each dataset before designing joins.
- Identify reliable business keys across source databases.
- Keep organisational hierarchy separate from product channel and insurance market.
- Prevent duplication when combining premium and claims data.
- Support portfolio, group, department and business-level reporting.

## Status

Initial project setup. The detailed data model will be developed after the business requirements and initial cross-database SQL exercises.
