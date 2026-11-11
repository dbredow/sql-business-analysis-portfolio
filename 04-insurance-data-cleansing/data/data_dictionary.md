# Initial Data Dictionary

The dataset contains 100 synthetic raw policy records from two source systems.

| Field | Description |
|---|---|
| RawRecordID | Generated identifier for the imported row |
| SourceSystem | Originating source system |
| SourcePolicyID | Source-system policy identifier |
| PolicyReference | Policy reference supplied by the source |
| BrokerName | Raw broker name |
| InsuredName | Raw insured/customer name |
| PolicyStatus | Raw policy status |
| InceptionDateRaw | Raw inception date text |
| ExpiryDateRaw | Raw expiry date text |
| WrittenPremiumRaw | Raw written premium text |
| CurrencyCodeRaw | Raw currency code or text |
| CommissionPctRaw | Raw commission percentage text |
| ReportingYearRaw | Raw reporting year text |
| CountryRaw | Raw country text |
| ImportBatchID | Import batch identifier |
| ImportedAt | Import timestamp |

All source values are retained in their raw form. Cleansing and standardisation will take place in downstream staging and output layers.
