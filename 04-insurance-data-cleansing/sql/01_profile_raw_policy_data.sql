/*
Project 04 — Insurance Data Cleansing & Standardisation
Script: 01_profile_raw_policy_data.sql
Purpose: Initial profiling of the untouched raw policy dataset.
Database: Cleansing
Table: raw_policy_data

These queries profile the data; they do not cleanse it.
Do not update or overwrite raw source values.
*/

USE Cleansing;

-- 1. Overall record and source profile
SELECT
    COUNT(*) AS TotalRecords,
    COUNT(DISTINCT SourceSystem) AS DistinctSystems,
    COUNT(DISTINCT SourcePolicyID) AS DistinctSourcePolicyIDs,
    COUNT(DISTINCT BrokerName) AS DistinctBrokerNames,
    COUNT(DISTINCT InsuredName) AS DistinctInsuredNames,
    COUNT(DISTINCT CurrencyCodeRaw) AS DistinctCurrencies
FROM raw_policy_data;

-- 2. Policy status profile
SELECT
    UPPER(TRIM(PolicyStatus)) AS NormalisedStatusForProfiling,
    COUNT(*) AS RecordCount
FROM raw_policy_data
GROUP BY UPPER(TRIM(PolicyStatus))
ORDER BY RecordCount DESC;

-- 3. Written premium completeness: mutually exclusive categories
SELECT
    SUM(CASE WHEN WrittenPremiumRaw IS NULL THEN 1 ELSE 0 END) AS NullWrittenPremium,
    SUM(CASE WHEN WrittenPremiumRaw = '' THEN 1 ELSE 0 END) AS EmptyWrittenPremium,
    SUM(CASE
            WHEN WrittenPremiumRaw IS NOT NULL
             AND WrittenPremiumRaw <> ''
             AND TRIM(WrittenPremiumRaw) = ''
            THEN 1 ELSE 0
        END) AS WhitespaceWrittenPremium
FROM raw_policy_data;

-- 4. Inception and expiry date completeness
SELECT
    SUM(CASE WHEN InceptionDateRaw IS NULL THEN 1 ELSE 0 END) AS NullInceptionDate,
    SUM(CASE WHEN InceptionDateRaw = '' THEN 1 ELSE 0 END) AS EmptyInceptionDate,
    SUM(CASE
            WHEN InceptionDateRaw IS NOT NULL
             AND InceptionDateRaw <> ''
             AND TRIM(InceptionDateRaw) = ''
            THEN 1 ELSE 0
        END) AS WhitespaceInceptionDate,
    SUM(CASE
            WHEN InceptionDateRaw IS NOT NULL
             AND InceptionDateRaw <> ''
             AND TRIM(InceptionDateRaw) <> ''
            THEN 1 ELSE 0
        END) AS InputtedInceptionDate,
    SUM(CASE WHEN ExpiryDateRaw IS NULL THEN 1 ELSE 0 END) AS NullExpiryDate,
    SUM(CASE WHEN ExpiryDateRaw = '' THEN 1 ELSE 0 END) AS EmptyExpiryDate,
    SUM(CASE
            WHEN ExpiryDateRaw IS NOT NULL
             AND ExpiryDateRaw <> ''
             AND TRIM(ExpiryDateRaw) = ''
            THEN 1 ELSE 0
        END) AS WhitespaceExpiryDate,
    SUM(CASE
            WHEN ExpiryDateRaw IS NOT NULL
             AND ExpiryDateRaw <> ''
             AND TRIM(ExpiryDateRaw) <> ''
            THEN 1 ELSE 0
        END) AS InputtedExpiryDate
FROM raw_policy_data;

-- 5. Inception date pattern profile
-- REGEXP recognises text shape only; it does not prove calendar validity.
SELECT
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN 1 ELSE 0 END) AS YYYY_MM_DD,
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{2}-[0-9]{2}-[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_MM_YYYY,
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{2}-[A-Za-z]{3}-[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_Mon_YYYY,
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{4}/[0-9]{2}/[0-9]{2}$' THEN 1 ELSE 0 END) AS YYYY_MM_DD_Slash,
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_MM_YYYY_Slash,
    SUM(CASE WHEN InceptionDateRaw REGEXP '^[0-9]{2}/[A-Za-z]{3}/[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_Mon_YYYY_Slash
FROM raw_policy_data;

-- 6. Expiry date pattern profile
SELECT
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN 1 ELSE 0 END) AS YYYY_MM_DD,
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{2}-[0-9]{2}-[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_MM_YYYY,
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{2}-[A-Za-z]{3}-[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_Mon_YYYY,
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{4}/[0-9]{2}/[0-9]{2}$' THEN 1 ELSE 0 END) AS YYYY_MM_DD_Slash,
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_MM_YYYY_Slash,
    SUM(CASE WHEN ExpiryDateRaw REGEXP '^[0-9]{2}/[A-Za-z]{3}/[0-9]{4}$' THEN 1 ELSE 0 END) AS DD_Mon_YYYY_Slash
FROM raw_policy_data;

-- 7. Targeted check for unexpected alphabetic text in expiry dates.
-- Excludes the two recognised abbreviated-month formats.
-- This is not a universal invalid-date check.
SELECT
    RawRecordID,
    SourceSystem,
    SourcePolicyID,
    ExpiryDateRaw
FROM raw_policy_data
WHERE ExpiryDateRaw NOT REGEXP '^[0-9]{2}-[A-Za-z]{3}-[0-9]{4}$'
  AND ExpiryDateRaw NOT REGEXP '^[0-9]{2}/[A-Za-z]{3}/[0-9]{4}$'
  AND ExpiryDateRaw REGEXP '[A-Za-z]';

-- Next: profile premium and commission formats, then validate dates
-- with explicit STR_TO_DATE masks and calendar-validity checks.
