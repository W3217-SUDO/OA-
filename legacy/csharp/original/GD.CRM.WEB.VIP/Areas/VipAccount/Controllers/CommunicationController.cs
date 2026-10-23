using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Account.Communication;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.Account.Communication;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.VipWeb.Areas.CRM.ViewModels;
using Dchien.Legal.Service.Account;
using Dchien.Legal.VipWeb.Areas.Account.ViewModels.Communication;
using Dchien.Legal.VipWeb.Controllers;
using Dchien.Legal.VipWeb.Models;
using Dchien.Legal.Service;

namespace Dchien.Legal.VipWeb.Areas.VipAccount.Controllers
{
    [CheckVipUserLogin]
    public class CommunicationController : Controller
    {
        internal Log Logger = new Log("Account.Controllers.CommunicationController");

        [HttpGet]
        public ActionResult Index(string id)
        {
            var model = new CommunicationListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="communicationId"></param>
        /// <param name="customerId"></param>
        /// <returns></returns>
        public ActionResult Communication(long? communicationId, int?customerId)
        {
            var model = new CommunicationModel();

            if (communicationId.HasValue)
            {
                model.Communication = CommunicationService.Instance.GetCommunication(communicationId.Value);
                var search = new CommunicationSearchCondition();
                search.CustomerId = model.Communication.CustomerId;
                search.PageNo = 1;
                search.PageSize = 15;
                model.CommunicationLogs = CommunicationService.Instance.GetCommunicationsByCustomer(search);
            }
            else if (customerId.HasValue)
            {
                model.Communication = new BizCommunication();
                model.Communication.CustomerId = customerId.Value;
                var customer = CustomerService.Instance.GetCustomerById(customerId.Value);
                if (customer != null)
                {
                    model.Communication.CustomerName =  customer.CustomerBasic.CustomerName;
                    model.Communication.CustomerNo =  customer.CustomerBasic.CustomerNo;

                    customer.ContactsList = ContactsService.Instance.GetCustomerContacts(customerId.Value);

                    if (customer.ContactsList != null && customer.ContactsList.Count > 0)
                    {
                        customer.DefaultContacts =
                            customer.ContactsList.FirstOrDefault(c => c.IsDefault == true && c.IsActived);

                        if (customer.DefaultContacts != null)
                        {
                            model.Communication.Contacts = customer.DefaultContacts.Contacts;
                            model.Communication.ContactPhone = customer.DefaultContacts.OfficePhone;
                        }
                    }
                }

                var search = new CommunicationSearchCondition();
                search.CustomerId = customerId;
                search.PageNo = 1;
                search.PageSize = 15;
                model.CommunicationLogs = CommunicationService.Instance.GetCommunicationsByCustomer(search);
            }
            else
            {
                model.Communication = new BizCommunication();
                model.CommunicationLogs = new List<BizCommunication>();
            }
            return PartialView(model);
        }

        [HttpPost]
        public ActionResult CommunicationLogList(long customerId)
        {
            var model = new CommunicationModel();
            if (customerId > 0)
            {
                var search = new CommunicationSearchCondition();
                search.CustomerId = customerId;
                search.PageNo = 1;
                search.PageSize = 15;
                model.CommunicationLogs = CommunicationService.Instance.GetCommunicationsByCustomer(search);
            }
            else
            {
                model.CommunicationLogs = new List<BizCommunication>();
            }

            return PartialView("CommunicationLogList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult List(CommunicationListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCommunicationSearchResultInfo();

                result.Communications = CommunicationService.Instance.GetCommunications(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;

                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(VipLoginHelper.GetClientIP(), VipLoginHelper.GetUserName(), "CommunicationController.List", "CommunicationController.List",ex);
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CreateUpdate(CommunicationModel model)
        {
            var response = new PostResponse();

            bool result = CommunicationService.Instance.CreateUpdate(model.Communication);

            if (result)
            {
                response.IsSuccess = true;
                response.Message = "保存成功.";
            }
            else
            {
                response.IsSuccess = false;
                response.Message = "保存失败.";
            }

            return Json(response);
        } 
    }
}
