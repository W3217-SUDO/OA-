using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAS.AP.Application;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.FCM.Contract.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.FCM.Contract.Audit;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.System.AuditFlow;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAS.AP;
using Dchien.Legal.Service.FAS.AP.Application;
using Dchien.Legal.Service.FAS.AR.CaseFee;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.Account.ViewModels.UserCenter;
using Dchien.Legal.Web.Areas.FCM.ViewModels.Contract;
using Dchien.Legal.Web.Areas.FCM.ViewModels.ContractPayment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractPaymentController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractPaymentController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ApplicationCreate(long contractId)
        {
            var model = new ApplicationCreateModel();
            model.Contract = ContractService.Instance.GetContractById(contractId);
            if (model.Contract.ContractBasicInfo.CustomerId.HasValue)
            {
                model.Customer = CustomerService.Instance.GetCustomerById(model.Contract.ContractBasicInfo.CustomerId.Value);
            }

            model.Application = new BizApplication();
            model.Application.ApplicationBasic = new BizApplicationBasic();
            model.Application.ApplicationBasic.ApplicationNo = "P" + DateTime.Now.ToString("yyMMdd") + "-" +
                                              new Random().Next(10000000, 99999999);
            model.Application.ApplicationBasic.ApplicationDate = DateTime.Now;
            model.Application.ApplicationBasic.Applicant = model.Contract.ContractBasicInfo.BusinessOwner;
            model.Application.ApplicationBasic.ApplicantName =
                UserService.Instance.GetUserByUserName(model.Contract.ContractBasicInfo.BusinessOwner).UserChName;

            model.Application.ApplicationBasic.CustomerName = model.Customer.CustomerName;

            model.Application.ApplicationBasic.PaidAmount = 0;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractObjectList(long? id)
        {
            var model = new ContractObjectListModel();

            return PartialView("ContractObjectList",model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
         [HttpPost]
         [CheckUserLogin]
         public JsonResult ContractObjects(long? contractId)
         {
             var response = new PostResponse();
             response.IsSuccess = true;
             var contractObjects = new List<BizContractObject>();

             if (contractId.HasValue && contractId > 0)
             {
                 contractObjects = ContractService.Instance.GetContractObjects(contractId.Value);
             }
             response.Data = contractObjects.Any() ? contractObjects.OrderBy(x => x.CaseId).ToList() : contractObjects;

             return Json(response);
         }




        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
         [HttpPost]
         public JsonResult ApplicationCreate(ApplicationCreateModel model)
        {
            var response = new PostResponse();

            try
            {
                bool result = ApplicationService.Instance.Apply(model.Application);

                if (result)
                {
                     response.Data = null;
                    response.Message = "提交成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "提交失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = true;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult PaymentTypeList()
         {
             var model = new Dchien.Legal.Web.Areas.FCM.ViewModels.ContractPayment.PaymentType.ListModel();

             return PartialView("PaymentType/List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentTypes(ListModel model)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var paymentTypeList = PaymentTypeService.Instance.GetPaymentTypeList(CaseFeeTypeId.Office);

            response.Data = paymentTypeList;

            return Json(response);
        }
    }
}
