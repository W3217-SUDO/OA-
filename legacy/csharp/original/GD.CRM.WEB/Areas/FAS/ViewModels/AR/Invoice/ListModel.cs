using Dchien.Legal.Entity.FAM.Invoice;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice
{
    /// <summary>
    /// 应付款申请列表
    /// </summary>
    public class ListModel 
	{
        public InvoiceSearchCondition SearchCondition { get; set; }

        public CaseFeeSearchCondition CaseFeeSearchCondition { get; set; }

	}
}
