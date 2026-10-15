
using Dchien.Legal.Entity.FAS.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.FAS.ViewModels.Cashed
{
    /// <summary>
    /// 
    /// </summary>
    public class IndexHistoryModel 
	{
        /// <summary>
        /// 到账管理
        /// </summary>
        public CaseFeeCashedSearchCondition SearchCondition { get; set; }

	}

    /// <summary>
    /// 
    /// </summary>
    public class CaseFeeAppliedListModel
    {
        public long CashedId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CaseFeeAppliedSearchCondition SearchCondition { get; set; }
    }
}
