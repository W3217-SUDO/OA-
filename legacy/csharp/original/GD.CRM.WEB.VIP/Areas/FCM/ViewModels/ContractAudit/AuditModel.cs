using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.FCM.Contract;


namespace Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit
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
        public long ContractId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string ContractNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizContract Contract { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public BizContractAudit ContractAudit { get; set; }
	}

    /// <summary>
    /// 
    /// </summary>
    public class AuditListModel
    {
        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string ContractNo { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public  List<BizContractAudit> ContractAuditList { get; set; }
    }
}





