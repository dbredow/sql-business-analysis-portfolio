Create View vw_uw_commission_brokerage as
select
	ReportingYear,
    ClassofBusiness,
    policyid,
    WrittenPremium,
    CommissionPCT,
    round(writtenpremium * commissionpct /100,2) as CommissionAmount,
    Brokeragepct,
    round(writtenpremium * brokeragepct /100,2) as BrokerageAmount
from abc_inhouse_premium.vw_uw_policy_detail
