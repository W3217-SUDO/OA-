using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AP.Payment.Audit;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Audit
{
    public class AuditModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public long AuditId { get; set; }
        
        /// <summary>
        /// 
        /// </summary>
        public long PaymentId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizPaymentAudit Audit { get; set; }
	}
}
