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
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class ArchiveSettlementController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.ArchiveSettlementController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList(string id)
        {

            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentObjectListModel();
            listModel.SearchCondition = new Entity.FAM.AR.ReceivedPayment.PaymentObjectSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            listModel.SearchCondition.SettlementStatus = (int)SettlementStatus.Paid;

            return View("PendingList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ProcessingList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentObjectListModel();
            listModel.SearchCondition = new Entity.FAM.AR.ReceivedPayment.PaymentObjectSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            listModel.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.P;

            return View("ProcessingList", listModel);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ProcessedList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentObjectListModel();
            listModel.SearchCondition = new Entity.FAM.AR.ReceivedPayment.PaymentObjectSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            listModel.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.Settlemented;
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
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.PaymentObjectListModel();
            listModel.SearchCondition = new Entity.FAM.AR.ReceivedPayment.PaymentObjectSearchCondition();

            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 10;
            listModel.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.Rejected;
            return View("RejectedList", listModel);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentIds"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ToAudit(string paymentObjectIds, string settlementRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentObjectIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentObjectService.Instance.ToAudit(long.Parse(x), settlementRemark, settlementRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentObjectIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ArchiveSettlementController.ToAudit", "ArchiveSettlementController.ToAudit", ex);
                response.IsSuccess = false;
                response.Message = "归档费申请结算出错.";
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
        public JsonResult Approved(string paymentObjectIds, string settlementAuditRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentObjectIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentObjectService.Instance.Approved(long.Parse(x), settlementAuditRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentObjectIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ArchiveSettlementController.Approved", "ArchiveSettlementController.Approved", ex);
                response.IsSuccess = false;
                response.Message = "标识已结算出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentObjectIds"></param>
        /// <param name="settlementAuditRemark"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Rejected(string paymentObjectIds, string settlementAuditRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentObjectIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentObjectService.Instance.Rejected(long.Parse(x), settlementAuditRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentObjectIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ArchiveSettlementController.Rejected", "ArchiveSettlementController.Rejected", ex);
                response.IsSuccess = false;
                response.Message = "拒绝结算出错.";
            }
            return Json(response);
        }

  
        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentObjectIds"></param>
        /// <param name="settlementRollbackRemark"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Rollback(string paymentObjectIds, string settlementRollbackRemark)
        {
            var response = new PostResponse();

            try
            {
                paymentObjectIds.Split(',').ToList().ForEach(x =>
                {
                    Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentObjectService.Instance.Rollback(long.Parse(x), settlementRollbackRemark);
                });
                response.IsSuccess = true;
                response.Data = paymentObjectIds;
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ArchiveSettlementController.Rollback", "ArchiveSettlementController.Rejected", ex);
                response.IsSuccess = false;
                response.Message = "归档费回滚出错.";
            }
            return Json(response);
        }

    }
}
