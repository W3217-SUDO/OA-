using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AR.Invoice;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice
{
    public class ViewModel 
	{
        /// <summary>
        /// 开票信息
        /// </summary>
        public BizInvoice Invoice { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public ViewMode? ViewMode { get; set; }

        public long? AuditId { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public enum ViewMode
    {
        Audit,
        Invoiced
    }
}
