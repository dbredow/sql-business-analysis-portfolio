START TRANSACTION;

UPDATE data_validation_results AS V
JOIN Staging_Policy_Data AS S
    ON V.RawRecordID = S.RawRecordID
SET V.WrittenPremiumStatus =
    CASE
        WHEN S.WrittenPremiumRaw REGEXP
             '^[0-9]+([.][0-9]{2})?$'
        THEN 'Valid'
        ELSE 'Exception'
    END
WHERE V.PipelineRunID = 1;
