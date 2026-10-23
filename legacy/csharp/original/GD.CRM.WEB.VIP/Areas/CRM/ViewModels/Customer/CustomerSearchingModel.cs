using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.Legal.Case;
namespace Dchien.Legal.Web.Areas.CRM.ViewModels.Customer
{
    public class CustomerSearchingModel
    {
        public BizCustomer Customer { get; set; }

        public BizCase Case { get; set; }

    }
}
