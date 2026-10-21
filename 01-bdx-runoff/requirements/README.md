# Business Requirements Analysis

## 1. Business Context

This project examines a BDX runoff settlement and export process. The objective is to translate business needs into clear requirements that support controlled settlement processing, accurate reporting, and reliable reconciliation.

## 2. Business Objectives

The process should support the following outcomes:

- Process settlement information consistently.
- Maintain traceability between payments and their allocations.
- Generate reporting outputs from validated data.
- Reconcile information between processing stages.
- Identify and manage exceptions.
- Maintain an audit trail of key processing and export activities.

## 3. Key Business Questions

The analysis considers questions such as:

1. How can the business establish that settlement information has been processed correctly?
2. How can payment allocations be traced back to their source?
3. What checks are needed before reporting outputs are generated?
4. How can differences between processing stages be identified and investigated?
5. What evidence is needed to demonstrate that an export was produced and controlled correctly?

## 4. Business Analysis Deliverables

- Business requirements and supporting rationale
- Process flow and business rules
- Logical data model
- Validation and reconciliation checks
- Test scenarios and expected results

## 5. Scope and Confidentiality

This is a sanitised portfolio summary, not a replacement for the original business requirements document. Examples will use synthetic or appropriately anonymised data, and confidential business information will not be published.

## 6. Status

**In progress** — initial business objectives and analysis questions have been defined. Detailed requirements, acceptance criteria, and supporting evidence will be developed as the project progresses.

## 7. Initial Acceptance Criteria

The following criteria are proposed for the portfolio proof of concept. They will be refined as the process and data model are developed.

| ID | Requirement | Acceptance criterion |
|---|---|---|
| AC01 | Settlement traceability | Each payment allocation can be traced to its source payment and relevant settlement record. |
| AC02 | Allocation integrity | The sum of allocations for a payment can be checked against the amount available for allocation, with any difference identified. |
| AC03 | Output validation | Required output fields are checked before an export is generated. |
| AC04 | Reconciliation | Differences between relevant processing stages can be identified and reported. |
| AC05 | Exception handling | Records that fail defined validation checks are flagged for investigation rather than silently treated as valid. |
| AC06 | Auditability | The proof of concept records enough information to demonstrate which validation checks were performed and their outcomes. |

### Acceptance Testing Approach

Each criterion will be tested using synthetic sample data that includes valid records and deliberately introduced exceptions. Expected results will be documented so that the actual results can be compared with them.

These are initial proposed criteria for the portfolio exercise, not confirmed requirements from the original business document.
