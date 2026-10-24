create view vw_uw_premium_class as
select
	ReportingYear,
    ClassofBusiness,
    count(policyid) as TotalPolicies,
    sum(WrittenPremium) as TotalWrittenPremium
From abc_inhouse_premium.vw_uw_policy_detail
Group by Reportingyear, Classofbusiness
