using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.AR.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.Payment;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AR.Payment;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using ListModel = Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ListModel;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class JARController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.ARController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_5001002001)]
        public ActionResult List(string id)
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new ContractSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PageId = id;
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_5001002001)]
        public ActionResult PaymentCreate(long contractId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.CreatePayment(contractId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(contractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
                model.Payment.PaymentBasic.PayerName = model.Customer == null ? string.Empty : model.Customer.CustomerBasic.CustomerName;
            }

            return View("Payment/Create", model);
        }

        [CheckUserLogin]
        public ActionResult PaymentEdit(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                var contract = ContractService.Instance.GetContractById(model.Payment.PaymentBasic.ContractId);
                contract.ContractBasicInfo.ARAmount = contract.ContractBasicInfo.ARAmount + model.Payment.PaymentBasic.CashedAmount - model.Payment.PaymentBasic.PrePaidAmount;
                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
                model.Payment.PaymentBasic.PayerName = model.Customer == null ? string.Empty : model.Customer.CustomerBasic.CustomerName;
            }

            return View("Payment/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="payment"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentCreateUpdate(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {
                bool result = PaymentService.Instance.PaymentCreateUpdate(payment);

                if (result)
                {
                    response.Message = "提交成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "提交失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ARController.PaymentCreateUpdate","ARController.PaymentCreateUpdate", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentView(long paymentId)
        {
            var model = new PaymentModel();

            var payment = PaymentService.Instance.GetPayment(paymentId);

            if (payment != null)
            {
                model.Payment = payment;
                var contract = ContractService.Instance.GetContractById(payment.PaymentBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("Payment/View",model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentList(long id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001002002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001002003)
              && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment.ListModel();

                model.SearchCondition = new PaymentSearchCondition();
                model.SearchCondition.PageId = id;
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;
                return View("Payment/List", model);
            }

            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Payment.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);
                result.TotalCashedAmount = PaymentService.Instance.GetCashedTotalAmount(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentList", "PaymentController.PaymentList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

    }
}
