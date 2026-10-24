Create View vw_uw_claims_policy as
with ClaimsPolicyCalc as (
	select
		Policyid,
        count(distinct claimid) as TotalDistinctClaims,
		sum(TotalClaimPayment) as TotalClaimPayment,
        sum(TotalRecovery) as TotalRecovery,
        sum(ReserveAmount) as TotalReserve,
        sum(TotalIncurred) as TotalIncurred
From ghi_inhouse_claims.vw_uw_claim_financials
Group by policyid)

select 
	p.policyid,
    cc.TotalDistinctClaims,
    cc.TotalClaimPayment,
    cc.TotalRecovery,
    cc.TotalReserve,
	cc.TotalIncurred
From abc_inhouse_premium.policy p
Left Join ClaimsPolicyCalc cc
on p.policyid = cc.policyid
