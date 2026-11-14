SELECT
    COUNT(*) AS RawRecords,
    SUM(CASE WHEN WrittenPremiumStatus = 'Valid' THEN 1 ELSE 0 END) AS ValidRecords,
    SUM(CASE WHEN WrittenPremiumStatus = 'Exception' THEN 1 ELSE 0 END) AS ExceptionRecords
FROM data_validation_results
WHERE PipelineRunID = 1;
