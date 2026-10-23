using System;
using System.Collections.Generic;

using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.HR.Staff;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerShare
{
    public class CustomerShareModel 
	{
        public BizCustomer Customer { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public List<Dchien.Legal.BizModel.HR.BizStaff> SharedObjects { get; set; }
	}
}

