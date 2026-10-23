using Dchien.Legal.BizModel.FAM.AR.CaseFee;
using Dchien.Legal.Entity.FAM.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.Cashed
{
    public class IndexModel 
	{
        /// <summary>
        /// 到账管理
        /// </summary>
        public BizCaseFeeCashed Cashed { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseFeeCashedSearchCondition CashedSearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseFeeSearchCondition CashUnsettledSearchCondition { get; set; }

	}
}
