using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Entity.CRM.Customer;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
{
    public class ListModel 
	{
        public List<BizCustomerType> CaseCustomerTypeList { get; set; }

        public ListModel()
        {
            this.SearchCondition = new CustomerSearchCondition();
        }
        public CustomerSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public CustomerTypeId CustomerTypeId { get; set; }
       
	}
}





