using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AP.CaseFee.Application;
using Dchien.Legal.BizModel.FAM.AP.CaseFee.Application.Audit;

namespace Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Audit
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
        public long ApplicationId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizCaseFeeApplicationAudit Audit { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class AuditListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long ApplicationId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string ApplicationNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseFeeApplicationAudit> AuditList { get; set; }
    }
}





