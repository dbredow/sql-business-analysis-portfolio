VIEW `order 1_vw_uw_policy_detail` AS
    SELECT 
        `p`.`PolicyID` AS `Policyid`,
        `p`.`WrittenPremium` AS `Writtenpremium`,
        `bi`.`BinderAgreementName` AS `BinderAgreementName`,
        `bi`.`UMR` AS `UMR`,
        `p`.`ReportingYear` AS `ReportingYear`,
        `c`.`ClassofBusiness` AS `ClassofBusiness`,
        `b`.`BusinessName` AS `BusinessName`,
        `br`.`BrokerName` AS `BrokerName`,
        `h`.`HandlerName` AS `HandlerName`,
        `p`.`PolicyReference` AS `Policyreference`,
        `p`.`PolicySeriesID` AS `PolicySeriesID`,
        `p`.`InceptionDate` AS `Inceptiondate`,
        `p`.`ExpiryDate` AS `ExpiryDate`,
        `p`.`CurrencyCode` AS `CurrencyCode`,
        `p`.`CommissionPCT` AS `CommissionPCT`,
        `p`.`BrokeragePCT` AS `BrokeragePCT`
    FROM
        (((((`policy` `p`
        LEFT JOIN `class` `c` ON ((`p`.`ClassID` = `c`.`Classid`)))
        LEFT JOIN `broker` `br` ON ((`p`.`BrokerID` = `br`.`BrokerID`)))
        LEFT JOIN `business` `b` ON ((`p`.`BusinessID` = `b`.`BusinessID`)))
        LEFT JOIN `handler` `h` ON ((`p`.`HandlerID` = `h`.`HandlerID`)))
        LEFT JOIN `binder` `bi` ON ((`p`.`BinderID` = `bi`.`BinderID`)))
