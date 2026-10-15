using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.AWS.OfficialDocument;

namespace Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentAudit
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
        public long OfficialDocumentId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string OfficialDocumentNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizOfficialDocument OfficialDocument { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizOfficialDocumentAudit OfficialDocumentAudit { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class AuditListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long OfficialDocumentId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string OfficialDocumentNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public  List<BizOfficialDocumentAudit> OfficialDocumentAuditList { get; set; }
    }
}





