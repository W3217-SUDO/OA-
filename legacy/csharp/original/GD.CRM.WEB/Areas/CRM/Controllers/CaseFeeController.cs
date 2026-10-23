using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CRM.ViewModels.CaseFee;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;

using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CaseFeeController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CaseFeeController");

        #region 批量下费用


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CaseFeeInform(long? customerId, long? contractId)
        {
            var model = new CaseFeeInformModel();

            if (customerId.HasValue)
            {
                var customer = CustomerService.Instance.GetCustomerById(customerId.Value);
                if (customer != null)
                {
                    model.CustomerId = customerId;
                    model.CustomerNo = customer.CustomerNo;
                    model.CustomerName = customer.CustomerName;
                }
            }

            model.CaseFees = new List<BizCaseFeeItem>();

            model.CaseFees.Add(new BizCaseFeeItem()
            {
                IsDefalut = true,
                InformDate = DateTime.Now
            });

            model.CaseFees.Add(new BizCaseFeeItem()
            {
                IsDefalut = false,
                InformDate = DateTime.Now
            });

            return PartialView(model);
        }

        #endregion
    }
}
