using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FAM.AR.ReceivedPayment;
using Dchien.Legal.BizModel.FAM.AR.CaseFee;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AR.ReceivedPayment;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class ARController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.ARController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult PaymentCreate()
        {
            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentModel();

            model.Payment = new BizModel.FAM.AR.ReceivedPayment.BizPayment();
            model.Payment.PaymentBasic = new BizPaymentBasic();
            model.Payment.PaymentBasic.CashedDate = DateTime.Now;
            model.Payment.PaymentBasic.SequenceNo = "R" + DateTime.Now.ToString("yyMMdd") + "-" + new Random().Next(10000000, 99999999);

            return View("ReceivedPayment/Create", model);
        }

        /// <summary>
        /// /
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult PaymentEdit(long paymentId)
        {
            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentModel();

            var payment = PaymentService.Instance.GetPaymentById(paymentId); 

            if(null == payment)
            {
                throw new ApplicationException("未找到回款信息.");
            }

            model.Payment = payment;
 
            return View("ReceivedPayment/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult PaymentPush(long paymentId)
        {
            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentModel();

            var payment = PaymentService.Instance.GetPaymentById(paymentId);

            if (null == payment)
            {
                throw new ApplicationException("未找到回款信息.");
            }

            model.Payment = payment;

            return View("ReceivedPayment/Push", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult PaymentApply(long paymentId)
        {
            var payment = PaymentService.Instance.GetPaymentById(paymentId);

            if(payment == null )
            {
                throw new ApplicationException("未找到相关回款记录.");
            }

            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentApplyModel();

            model.Payment = payment;
            model.SearchCondition = new PaymentObjectSearchCondition();
            model.SearchCondition.CustomerName = payment.PaymentBasic.CustomerName;
            model.SearchCondition.ContractNo = payment.PaymentBasic.ContractNo;
            model.SearchCondition.PaymentId = payment.PaymentBasic.PaymentId;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;

            return View("ReceivedPayment/Apply", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult RefundApply(long paymentId)
        {
            var payment = PaymentService.Instance.GetPaymentById(paymentId);

            if (payment == null)
            {
                throw new ApplicationException("未找到相关回款记录.");
            }

            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentApplyModel();

            model.Payment = payment;
            model.SearchCondition = new PaymentObjectSearchCondition();
            model.SearchCondition.CustomerName = payment.PaymentBasic.CustomerName;
            model.SearchCondition.ContractNo = payment.PaymentBasic.ContractNo;
            model.SearchCondition.PaymentId = payment.PaymentBasic.PaymentId;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;

            return View("ReceivedPayment/RefundApply", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult PaymentApplied(long paymentId)
        {
            var payment = PaymentService.Instance.GetPaymentById(paymentId);

            if (payment == null)
            {
                throw new ApplicationException("未找到相关回款记录.");
            }

            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentAppliedModel();

            model.Payment = payment;
            model.SearchCondition = new PaymentObjectSearchCondition();
            model.SearchCondition.PaymentId = payment.PaymentBasic.PaymentId;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;
 
            return View("ReceivedPayment/Applied", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        public ActionResult PaymentAppliedView(long paymentId)
        {
            var payment = PaymentService.Instance.GetPaymentById(paymentId);

            if (payment == null)
            {
                throw new ApplicationException("未找到相关回款记录.");
            }

            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentAppliedModel();

            model.Payment = payment;
            model.SearchCondition = new PaymentObjectSearchCondition();
            model.SearchCondition.PaymentId = payment.PaymentBasic.PaymentId;
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 100;

            return View("ReceivedPayment/AppliedView", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentList(string id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001002002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001002003
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001002004
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001001002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001001003
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001001004
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001001005)
                && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
                listModel.SearchCondition = new PaymentSearchCondition();

                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("ReceivedPayment/List", listModel);
            }

            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="searchCondition"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult PaymentObjectAppliedList(PaymentObjectSearchCondition searchCondition)
        {
            var response = new PostResponse();

            try
            {
                if (searchCondition.PageNo == 0)
                    searchCondition.PageNo = 1;
                if (searchCondition.PageSize == 0)
                    searchCondition.PageSize = 100;

                var model = new PaymentObjectListModel();


                model.Payment = PaymentService.Instance.GetPaymentById(searchCondition.PaymentId.Value);
                model.Payment.PaymentObjects = PaymentService.Instance.GetPaymentObjectList(searchCondition);

                model.TotalCount = searchCondition.TotalCount;
                model.PageNo = searchCondition.PageNo;
                model.PageSize = searchCondition.PageSize;

                return PartialView("ReceivedPayment/PartialView/PaymentObjectAppliedList", model);

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentObjectAppliedList", "ReceivedPaymentController.PaymentObjectAppliedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="searchCondition"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult PaymentObjectList(PaymentObjectSearchCondition searchCondition)
        {
            var response = new PostResponse();

            try
            {
                if (searchCondition.PageNo == 0)
                    searchCondition.PageNo = 1;
                if (searchCondition.PageSize == 0)
                    searchCondition.PageSize = 100;

                var model = new PaymentObjectListModel();

                model.Payment = PaymentService.Instance.GetPaymentById(searchCondition.PaymentId.Value);

                var search = new Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();

                search.PaymentReceviedStatus = (int)Dchien.Legal.Entity.FAM.AR.CaseFee.PaymentReceviedStatus.UnRecevied;
                search.CustomerName = searchCondition.CustomerName;
                search.ContractNo = searchCondition.ContractNo;
                search.CaseNo = searchCondition.CaseNo;
                search.CaseTypeId = searchCondition.CaseTypeId;
                search.CasePhaseId = searchCondition.CasePhaseId;
                search.CaseFeeTypeId = searchCondition.CaseFeeTypeId;
                search.CompanyId = LoginHelper.GetCompanyId();
                search.PageSize = searchCondition.PageSize;
                search.PageNo = searchCondition.PageNo;

                var caseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeList(search);

                 model.Payment.PaymentObjects = new List<BizPaymentObject>();

                caseFeeList.ForEach(x =>
                {
                    var paymentObject = new BizPaymentObject();

                    paymentObject.CaseFeeId = x.CaseFeeId;
                    paymentObject.CaseId = x.CaseId;
                    paymentObject.CaseNo = x.CaseNo;
                    paymentObject.CaseFeePayAmount = x.UnCashedAmount;

                    model.Payment.PaymentObjects.Add(paymentObject);
                });

                model.TotalCount = search.TotalCount;
                model.PageNo = search.PageNo;
                model.PageSize = search.PageSize;

                return PartialView("ReceivedPayment/PartialView/PaymentObjectList", model);

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentObjectList", "ReceivedPaymentController.PaymentObjectList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeList(Dchien.Legal.Entity.FAM.AR.CaseFee.CaseFeeSearchCondition searchCondition)
        {
            var response = new PostResponse();

            try
            {
                if (searchCondition.PageNo == 0)
                    searchCondition.PageNo = 1;
                if (searchCondition.PageSize == 0)
                    searchCondition.PageSize = 15;

                var result = new BizCaseFeeSearchResultInfo();

                if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.All)
                {
                    searchCondition.CompanyId = LoginHelper.GetCompanyId();
                }
                else
                {
                    searchCondition.UserId = LoginHelper.GetUserName();
                }

                result.CaseFeeList = CaseFeeService.Instance.GetCaseFeeList(searchCondition);

                result.TotalItemCount = searchCondition.TotalCount;
                result.PageNo = searchCondition.PageNo;
                result.PageSize = searchCondition.PageSize;
                result.TotalAmount = searchCondition.TotalAmount;
                result.TotalCashedAmount = searchCondition.TotalCashedAmount;
                result.TotalPaidAmount = searchCondition.TotalPaidAmount;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.CaseFeeList", "ARController.CaseFeeList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult AuditList(string id)
        { 
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
                listModel.SearchCondition = new PaymentSearchCondition();

                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("Audit/List", listModel);
          
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult PaymentList(long caseFeeId)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentListModel();
            listModel.PaymentList = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentListByCaseFeeId(caseFeeId);
            return PartialView("ReceivedPayment/PartialView/PaymentList", listModel);
        }

        #region 工行
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ICBCList()
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ICBC.ICBCListModel();
            return View("ICBC/ICBCList", listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ICBCImport()
        {
             return PartialView("ICBC/ICBCImport");
        }

        #endregion 

        #region 中行
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult BOCList()
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.BOC.BOCListModel();
            return View("BOC/BOCList", listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult BOCImport()
        {
            return PartialView("BOC/BOCImport");
        }

        #endregion 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult CaseFeeList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFee.CaseFeeListModel();

            listModel.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition(); 
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;

            return View("CaseFeeList", listModel);

        }

    }



}
