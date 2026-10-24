Create View 02_vw_uw_claim_detail as 
with ClaimTransactionCalc as (
	select
		Claimid,
        sum(case when transactiontype = 'Payment' then transactionamount else 0 end) TotalClaimPayment,
        sum(case when transactiontype = 'Recovery' then transactionamount else 0 end) TotalRecovery
	from Claim_transaction
    Group by ClaimID)
select
	c.claimid,
    c.claimReference,
    c.claimStatus,
    c.reserveAmount,
    coalesce(cc.TotalClaimPayment,0) as TotalClaimPayment,
    coalesce(cc.TotalRecovery,0) as TotalRecovery,
    coalesce(totalclaimpayment - TotalRecovery, 0) as TotalIncurred
From Claim c
left join ClaimTransactionCalc cc
on c.claimid = cc.claimid
