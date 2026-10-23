using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AR.Invoice;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice.Audit
{
    public class AuditModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public long? AuditId { get; set; }
        
        /// <summary>
        /// 
        /// </summary>
        public long InvoiceId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizInvoiceAudit InvoiceAudit { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class AuditListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long InvoiceId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string InvoiceNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizInvoiceAudit> InvoiceAuditList { get; set; }
    }
}





