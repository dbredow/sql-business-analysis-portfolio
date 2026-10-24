create view vw_uw_claims_class as
select
	pd.Reportingyear,
    pd.ClassofBusiness,
    count(distinct pd.policyid) as TotalPolicies,
    sum(pd.WrittenPremium) as TotalWrittenPremium,
    coalesce(sum(cp.TotalDistinctClaims),0) as TotalClaims,
    sum(cp.TotalClaimPayment) as TotalClaimPayment,
    sum(cp.TotalRecovery) as TotalRecovery,
    sum(cp.TotalReserve) as TotalReserve,
    sum(cp.TotalIncurred) as TotalIncurred
from abc_inhouse_premium.vw_uw_policy_detail pd
left join abc_inhouse_premium.vw_uw_claim_policy cp
on pd.policyid = cp.policyid

group by pd.reportingyear, pd.Classofbusiness
