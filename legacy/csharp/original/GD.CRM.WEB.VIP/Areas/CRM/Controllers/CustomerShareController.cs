using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.CRM.Customer;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerShare;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerShareController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerShareController");

        [CheckUserLogin]
        public ActionResult Sharing(long customerId)
        {
            var model = new CustomerShareModel();
            var customer = CustomerService.Instance.GetCustomerById(customerId);
            model.Customer = customer;

            return PartialView("Sharing", model);
        }

        [CheckUserLogin]
        public JsonResult CustomerSharing(long customerId, List<string> sharedObjects)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            bool result = CustomerService.Instance.CustomerSharing(customerId, sharedObjects);

            if (!result)
            {
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult CustomerSharedObjects(long customerId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            var sharedObjects = CustomerService.Instance.GetCustomerCoordinatorByCustomerId(customerId);

            if (sharedObjects == null)
            {
                sharedObjects = new List<BizCustomerCoordinator>();
                sharedObjects.Add(new BizCustomerCoordinator());
            }

            response.Data = sharedObjects;

            return Json(response);
        }

    }
}
