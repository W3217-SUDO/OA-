using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerEvent
{
    public class CustomerEventListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCustomerEvent> CustomerEvents { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long ContractId { get; set; }

	}
}

