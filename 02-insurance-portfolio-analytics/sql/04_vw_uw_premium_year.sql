create view vw_uw_premium_year as
select
	ReportingYear,
    count(policyid) as TotalPolicyCount,
    sum(writtenpremium) as TotalWrittenPremium
From abc_inhouse_premium.vw_uw_policy_detail 
Group by ReportingYear
