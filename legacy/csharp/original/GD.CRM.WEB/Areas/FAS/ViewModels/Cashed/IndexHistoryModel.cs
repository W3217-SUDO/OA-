
using Dchien.Legal.Entity.FAM.AR.CaseFee;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.Cashed
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
