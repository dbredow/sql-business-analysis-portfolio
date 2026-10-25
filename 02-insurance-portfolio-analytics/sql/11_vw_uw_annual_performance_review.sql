create view vw_uw_annual_performance_review as
With RenewalPerforamnceCalc as (
	Select
		ReportingYear,
        ClassofBusiness,
        count(*) as TotalPolicies,
        sum(WrittenPremium) as TotalWrittenPremium

From abc_inhouse_premium.vw_uw_policy_detail

Group by ReportingYear, ClassofBUsiness),

LagLeadPremiumPolicy as (
Select 
	ReportingYear,
	ClassofBusiness,
	TotalWrittenPremium,
    Totalpolicies,
	Lag	(TotalWrittenPremium) over (partition by classofbusiness order by Reportingyear) as PreviousYearWrittenPremium,
    Lead (TotalWrittenPremium) over (partition by classofbusiness order by Reportingyear) as ForwardYearWrittenPremium,
	Lag	(TotalPolicies) over (partition by classofbusiness order by Reportingyear) as PreviousTotalPolicies,
    Lead (TotalPolicies) over (partition by classofbusiness order by Reportingyear) as ForwardTotalPolicies
   from RenewalPerforamnceCalc)

Select
ReportingYear,
ClassofBusiness,
TotalWrittenPremium,
PreviousYearWrittenPremium,
ForwardYearWrittenPremium,
round((TotalWrittenPremium - PreviousYearWrittenPremium) / nullif(PreviousYearWrittenPremium,0) *100,2) as PremiumChangePCT,
TotalPolicies,
PreviousTotalPolicies,
ForwardTotalPolicies,
round((TotalPolicies - PreviousTotalPolicies) / nullif(PreviousTotalPolicies,0) *100,2) as PolicyChangePCT 
from LagLeadPremiumPolicy 
