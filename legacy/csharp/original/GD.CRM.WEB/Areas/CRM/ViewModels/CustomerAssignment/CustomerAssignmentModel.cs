using System;
using System.Collections.Generic;
using Dchien.Legal.BizModel.CRM.Customer;

using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerAssignment
{
    public class CustomerAssignmentModel 
	{

        public BizCustomer Customer { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public string AssigningCustomerOwner { get; set; }

        public string AssigningCustomerOwnerName { get; set; }


	}
}

