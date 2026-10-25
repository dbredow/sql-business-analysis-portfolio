Create view vw_uw_broker_performance as
with BrokerNameRanked as (
select
	ReportingYear,
    BrokerName,
    count(*) as TotalPolicies, 
    sum(writtenpremium) as TotalWrittenPremium,
    avg(writtenpremium) as AvgPolicyWrittenPremium

From abc_inhouse_premium.vw_uw_policy_detail

Group by ReportingYear, Brokername)

Select
	ReportingYear,
    Brokername,
    TotalPolicies,
    TotalWrittenPremium,
    AvgPolicyWrittenPremium,
    dense_rank () over (partition by ReportingYear order by totalwrittenpremium desc) as BrokerNamesRanked
From BrokerNameRanked
