Create view vw_uw_data_quality as
select
	policyid,
    policyreference,
    Reportingyear,
	'Invalid policy dates' AS IssueDescription
from abc_inhouse_premium.vw_uw_policy_detail
where inceptiondate > expirydate

UNION ALL

select
	policyid,
    policyreference,
    Reportingyear,
    'Missing or negative premium' AS IssueDescription
from abc_inhouse_premium.vw_uw_policy_detail
where writtenpremium < 0 or writtenpremium is null 

UNION ALL	

select
	policyid,
    policyreference,
    Reportingyear,
    'CommissionPCT Range' AS IssueDescription
from abc_inhouse_premium.vw_uw_policy_detail
where commissionpct not  between 5 and 15
	or Commissionpct is null
UNION ALL

select
	policyid,
    policyreference,
    Reportingyear,
	'BrokeragePCT Range' AS IssueDescription
from abc_inhouse_premium.vw_uw_policy_detail
where brokeragepct not  between 20 and 30
	or brokeragepct is null
