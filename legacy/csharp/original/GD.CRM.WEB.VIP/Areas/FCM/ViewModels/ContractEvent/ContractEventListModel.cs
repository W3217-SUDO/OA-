using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FCM.ViewModels.ContractEvent
{
    public class ContractEventListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizContractEvent> ContractEvents { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }

	}
}

