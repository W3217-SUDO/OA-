using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Service.CRM.Customer.File;
using Dchien.Legal.Service.CRM.Customer.Event;
using Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerEvent;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using BizCustomerFile = Dchien.Legal.BizModel.CRM.Customer.BizCustomerFile;


namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerEventController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerEventController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CustomerEventList()
        {
            var model = new CustomerEventListModel();

            return PartialView("CustomerEventList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ViewCustomerEventList()
        {
            var model = new CustomerEventListModel();

            return PartialView("View/CustomerEventList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerGuid"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult CustomerEvents(string customerGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var events = new List<BizCustomerEvent>();

            if (!string.IsNullOrEmpty(customerGuid))
            {
                events = CustomerEventService.Instance.GetCustomerEventList(customerGuid);
            }

            response.Data = events;

            return Json(response);
        }

        [CheckUserLogin]
        public ActionResult CustomerEvent()
        {
            var model = new CustomerEventModel();

            return PartialView("CustomerEvent", model);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerGuid"></param>
        /// <param name="content"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult CustomerEventCreate(string customerGuid,string content)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var customerEvent = new BizCustomerEvent();

            customerEvent.CustomerGuid = customerGuid;
            customerEvent.Content = content;
            customerEvent.OperateTime = DateTime.Now;

            CustomerEventService.Instance.Create(customerEvent);

            return Json(response);
        }
    }
}
