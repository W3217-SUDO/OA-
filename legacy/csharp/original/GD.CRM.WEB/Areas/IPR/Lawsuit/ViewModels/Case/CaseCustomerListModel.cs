using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseCustomerListModel 
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCustomer> CaseCustomers { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}
}





