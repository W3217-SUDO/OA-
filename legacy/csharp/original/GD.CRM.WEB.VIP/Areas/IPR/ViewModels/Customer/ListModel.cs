using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.Customer;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.Customer
{
    public class ListModel 
	{
        public List<BizCustomerType> CaseCustomerTypeList { get; set; }
	}
}





