using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit
{
    public class ContractAuditListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizContractAudit> ContractAudits { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }


	}
}

