using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.CRM.Customer;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseCustomerSelectedModel 
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizCustomer> Customers { get; set; }

        public CustomerSearchCondition SearchCondition { get; set; }

        public long CaseId { get; set; }

        public int CustomerTypeId { get; set; }

	}
}





