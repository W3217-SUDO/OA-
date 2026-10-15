using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.CRM.Customer;

using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerEvent
{
    public class CustomerEventModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public BizCustomerEvent CustomerEvent { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public string CustomerId { get; set; }

	}
}

