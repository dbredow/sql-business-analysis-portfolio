INSERT INTO data_quality_exceptions (
    PipelineRunID,
    RawRecordID,
    FieldName,
    OriginalValue,
    ExceptionType,
    ExceptionDescription,
    RaisedAt
)
SELECT
    1,
    S.RawRecordID,
    'WrittenPremium',
    S.WrittenPremiumRaw,
    'Invalid Format',
    'Written Premium does not match the agreed numeric format.',
    NOW()
FROM Staging_Policy_Data AS S
JOIN data_validation_results AS V
    ON S.RawRecordID = V.RawRecordID
WHERE V.PipelineRunID = 1
  AND V.WrittenPremiumStatus = 'Exception';
