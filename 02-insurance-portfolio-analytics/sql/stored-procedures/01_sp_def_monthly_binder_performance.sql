DELIMITER $$

CREATE PROCEDURE sp_DEF_MonthlyBinderPerformance(
	IN p_Reportingmonth tinyint,
    IN p_ReportingYear smallint)
    
BEGIN

With Premcalc as (
	select
		policyid,
        reportingmonth,
        reportingyear,
		sum(premiumamount) as TotalPremium
	from def_third_party_broking.premiumdeclaration
	
    WHERE ReportingYear = p_ReportingYear
		AND ReportingMonth = p_ReportingMonth
    
    Group by policyid, reportingmonth, reportingyear),

CLaimsCalc as (
	select 
		policyreference,
        reportingmonth,
        reportingyear,
        sum(paidamount) as GrossPaidClaims,
        sum(Recoveryamount) as TotalRecoveries,
        sum(paidamount) - sum(recoveryamount) as NetPaidClaims
	from jkl_third_party_claims.claimsdeclaration
	
    WHERE ReportingYear = p_ReportingYear
		AND ReportingMonth = p_ReportingMonth
    
    group by policyreference, reportingmonth, reportingyear),
    
 PolicyPerformance as (
	select
        p.policyid,
		pc.TotalPremium,
        cc.NetPaidClaims,
        p.Binderid,
        p.policyreference,
        pc.reportingmonth,
        pc.reportingyear
    from def_third_party_broking.policy p
    left join premcalc pc
    on p.policyid = pc.policyid
    left join claimscalc cc
    on p.policyreference = cc.policyreference
    and pc.reportingmonth = cc.reportingmonth
    and pc.reportingyear = cc.reportingyear
    
    WHERE pc.PolicyID IS NOT NULL)
    
Select
		b.binderagreementName,
		pp.reportingmonth,
        pp.reportingyear,
        round(sum(pp.TotalPremium),2) as TotalPremiumAmount,
        round(SUM(pp.TotalPremium) * b.BrokeragePct / 100,2) as Totalbrokerageamount,
        SUM(COALESCE(pp.NetPaidClaims, 0)) as TotalNetPaidClaims,
        round(CASE WHEN SUM(pp.TotalPremium) <= 0 THEN NULL ELSE SUM(COALESCE(pp.NetPaidClaims, 0)) / SUM(pp.TotalPremium) * 100 END,2) As TotalLossRatio
from policyperformance pp
left join def_third_party_broking.binders b
on pp.binderid = b.binderid
group by b.binderid, b.binderagreementname, pp.reportingmonth, pp.reportingyear;

END$$ 

DELIMITER ;
