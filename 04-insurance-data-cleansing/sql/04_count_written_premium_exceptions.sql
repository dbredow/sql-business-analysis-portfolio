SELECT COUNT(*) AS ExceptionCount
FROM data_quality_exceptions
WHERE PipelineRunID = 1
  AND FieldName = 'WrittenPremium';
