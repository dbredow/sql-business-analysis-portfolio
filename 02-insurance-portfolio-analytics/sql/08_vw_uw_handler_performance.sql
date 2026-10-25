Create view vw_uw_handler_performance as
with HandlersNameRanked as (
select
	ReportingYear,
    HandlerName,
    count(*) as TotalPolicies, 
    sum(writtenpremium) as TotalWrittenPremium,
    avg(writtenpremium) as AvgPolicyWrittenPremium

From abc_inhouse_premium.vw_uw_policy_detail

Group by ReportingYear, Handlername)

Select
	ReportingYear,
    Handlername,
    TotalPolicies,
    TotalWrittenPremium,
    AvgPolicyWrittenPremium,
    dense_rank () over (partition by ReportingYear order by totalwrittenpremium desc) as HandlerNamesRanked
From HandlersNameRanked
