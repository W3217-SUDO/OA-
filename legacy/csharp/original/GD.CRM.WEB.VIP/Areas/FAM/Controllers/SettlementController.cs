using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Web.UI.WebControls;
using System;
using System.Text;
using System.Web;
using System.Web.UI;
using System.IO;

using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class SettlementController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.SettlementController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList(string id)
        {

            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
            listModel.SearchCondition = new Dchien.Legal.Entity.FAM.AR.ReceivedPayment.PaymentSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            return View("PendingList", listModel);

        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult ToAuditCreate()
        {
            return PartialView("PartialView/ToAudit");
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult AuditApproved()
        {
            return PartialView("PartialView/Approved");
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult AuditRejected()
        {
            return PartialView("PartialView/Rejected");
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult AuditRollback()
        {
            return PartialView("PartialView/Rollback");
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult AuditPaid()
        {
            return PartialView("PartialView/Paid");
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ProcessingList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
            listModel.SearchCondition = new Dchien.Legal.Entity.FAM.AR.ReceivedPayment.PaymentSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            return View("ProcessingList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingPaymentList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
            listModel.SearchCondition = new Dchien.Legal.Entity.FAM.AR.ReceivedPayment.PaymentSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            return View("PendingPaymentList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ProcessedList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
            listModel.SearchCondition = new Dchien.Legal.Entity.FAM.AR.ReceivedPayment.PaymentSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            return View("ProcessedList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult RejectedList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel();
            listModel.SearchCondition = new Dchien.Legal.Entity.FAM.AR.ReceivedPayment.PaymentSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            return View("RejectedList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ToAudit(string paymentIds, string settlementRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.ToAudit(long.Parse(x), settlementRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SettlementController.ToAudit", "SettlementController.ToAudit", ex);
                response.IsSuccess = false;
                response.Message = "申请结算出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Approved(string paymentIds,string settlementAuditRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.Approved(long.Parse(x), settlementAuditRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SettlementController.Approved", "SettlementController.Approved", ex);
                response.IsSuccess = false;
                response.Message = "已结算出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Paid(string paymentIds, string settlementPaidRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.Paid(long.Parse(x), settlementPaidRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SettlementController.Paid", "SettlementController.Paid", ex);
                response.IsSuccess = false;
                response.Message = "标记已支付出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Rejected(string paymentIds, string settlementAuditRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.Rejected(long.Parse(x), settlementAuditRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SettlementController.Rejected", "SettlementController.Rejected", ex);
                response.IsSuccess = false;
                response.Message = "拒绝结算出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Rollback(string paymentIds, string settlementRollRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.Rollback(long.Parse(x), settlementRollRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "SettlementController.Rollback", "SettlementController.Rollback", ex);
                response.IsSuccess = false;
                response.Message = "回退结算出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult SettlementListSelectedExportToExcel(List<string> caseNos)
        {
            var fileName = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.ExportSettlementManifestToExcel(caseNos.Distinct().ToList());
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ExportSettlementManifestToExcel(List<long> paymentIds)
        {
            var paymentObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentObjectList(paymentIds);
            var caseNos = paymentObjects.Select(x => x.CaseNo);
            var fileName = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.ExportSettlementManifestToExcel(caseNos.Distinct().ToList());
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ExportSettlementHeaderManifestToExcel(List<long> paymentIds)
        {
            var paymentObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentObjectList(paymentIds);
            var caseNos = paymentObjects.Select(x => x.CaseNo);
            var fileName = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.ExportSettlementHeaderManifestToExcel(caseNos.Distinct().ToList());
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ExportSettlementItemManifestToExcel(List<long> paymentIds)
        {
            var paymentObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentObjectList(paymentIds);
            var caseNos = paymentObjects.Select(x => x.CaseNo);
            var fileName = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.ExportSettlementItemManifestToExcel(caseNos.Distinct().ToList());
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentObjectIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult SettlementObjectListSelectedExportToExcel(List<long> paymentObjectIds)
        {
            var fileName = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentObjectService.Instance.PaymentObjectListSelectedExportToExcel(paymentObjectIds.Distinct().ToList());
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

    }
}
