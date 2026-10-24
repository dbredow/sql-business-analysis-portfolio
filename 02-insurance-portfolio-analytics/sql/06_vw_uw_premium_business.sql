create view vw_uw_premium_business as
select
	ReportingYear,
    BusinessName,
    count(policyid) as TotalPolicies,
    sum(WrittenPremium) as TotalWrittenPremium
From abc_inhouse_premium.vw_uw_policy_detail
Group by Reportingyear, businessName
