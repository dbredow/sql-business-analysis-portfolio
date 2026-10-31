# GadgetClient — Technical Review Notes

## Review scope

Reviewed the supplied `mapping_gui_v15.py` source and four accompanying PDF documents:

- End-to-end data flow and architecture.
- Client Database v15 summary.
- Email notifications v14.
- Folder structure explanation (versions 1–14).

The Client Admin GUI source and `client_db_v15.py` implementation were not supplied, so those components could only be assessed from the documentation and import contracts.

## Corrections applied to the portfolio copy of the mapping engine

1. Repaired malformed success- and failure-notification `try/except` blocks that prevented Python compilation.
2. Corrected the module-level `global` declaration for resolved client identity values.
3. Removed a duplicated client database mapping block that was immediately reset later in the same function.
4. Made the optional `openpyxl` import consistent, avoiding a later unconditional import that bypassed the optional-dependency check.
5. Corrected email recipient handling so per-client TO/CC overrides are used as SMTP envelope recipients, not merely displayed in message headers.
6. Corrected mapping precedence to follow the documented intent: client database mappings take priority over saved per-client mappings, which take priority over auto-suggestions.
7. Updated stale script header and command-line description version labels.

These are targeted repairs to the supplied portfolio copy. They are not a substitute for regression testing against real application fixtures.

## Findings and outstanding work

### 1. Missing runtime components

The mapping engine imports `client_db_v15.py`, but that module was not included. The architecture documentation also describes a Client Admin GUI, but its source was not included. The full application therefore cannot currently be launched from this repository alone.

### 2. Configuration and portability

The source uses a hard-coded Windows base directory (`C:\\GadgetClient`). A future improvement would be to load the base path from a configuration file or environment variable.

SMTP settings are read from `inbox_config.json`. Keep the real file out of version control and use secret storage or environment-specific configuration for credentials.

### 3. Documentation version alignment

The supplied documents describe several points in the product's evolution:

- Folder structure documentation covers versions 1–14.
- Email notification documentation is labelled v14.
- Client database summary is v15.
- Data flow documentation describes Mapping GUI v13.1 and a recommended final connection patch.
- The supplied processing source is named v15.

The README describes the intended architecture while preserving the fact that some supplied documentation is historical. A future documentation pass should identify exactly which behaviours are implemented in the current source and which remain planned.

### 4. Test coverage required before production use

Recommended test cases include:

- Header mapping precedence: client database vs saved mapping vs auto-suggestion.
- Exact, alias, fuzzy and unresolved client identity matching.
- Required-field and row-level validation.
- Date, numeric and premium parsing, including malformed values.
- Duplicate, missing and unexpected records.
- Invoice totals, tax calculations and control totals.
- Per-client and master bordereau reconciliation.
- Failure-pack creation and safe retry behaviour.
- Email success/failure paths and per-client recipient overrides.
- Inbox processing in one-off and watch modes.

Use synthetic data and assert that source files are not silently lost or overwritten.

## Static validation performed

- `python -m py_compile src/mapping_gui_v15.py` — passed after the targeted repairs.
- Full runtime execution — not performed; PySimpleGUI and `client_db_v15.py` were not available in the supplied runtime.

## Publication assessment

The project is suitable for a portfolio case study when clearly labelled as a proof of concept and when only synthetic/anonymised data and non-secret configuration examples are published. Do not describe it as production-ready until the missing components and regression tests are supplied and completed.
