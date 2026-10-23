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
using Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerAssignment;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using log4net.Repository.Hierarchy;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerAssignmentController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerAssignmentController");

        [CheckUserLogin]
        public ActionResult CustomerList()
        {
            var model = new ListModel();

            model.SearchCondition = new CustomerSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }

        [CheckUserLogin]
        public ActionResult Assigning(long customerId)
        {
            var model = new CustomerAssignmentModel();
            var customer = CustomerService.Instance.GetCustomerById(customerId);
            model.Customer = customer;

            return PartialView("Assigning", model);
        }

        [CheckUserLogin]
        public JsonResult CustomerAssigning(long customerId, string assigningCustomerOwner)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var customerIds = new List<long>();

            customerIds.Add(customerId);

            CustomerService.Instance.CustomerOwnerChange(customerIds, assigningCustomerOwner);

            return Json(response);
        }

    }
}
