using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.Customer
{
    public class LicenseModel 
	{
        /// <summary>
        /// 客户Id
        /// </summary>
	    public int CustomerId{ get; set; }

        /// <summary>
        /// 客户No
        /// </summary>
        public string CustomerNo { get; set; }

	}
}





