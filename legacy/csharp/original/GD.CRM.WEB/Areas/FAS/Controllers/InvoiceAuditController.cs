using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.AR.Invoice;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.AR.Invoice;
using Dchien.Legal.Service.FAM.AR.Invoice.Audit;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.Invoice.Audit;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceAuditController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceAuditController");
  
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.InvoiceStatus = InvoiceStatus.P;
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.InvoiceStatus = InvoiceStatus.P;
                model.SearchCondition.Auditor = LoginHelper.GetUserName();

                var result = new BizInvoiceSearchResultInfo();

                result.InvoiceList = InvoiceService.Instance.GetPendingInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ApprovedList()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.InvoiceStatus  = InvoiceStatus.A;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ApprovedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.Auditor = LoginHelper.GetUserName();

                var result = new BizInvoiceSearchResultInfo();

                result.InvoiceList = InvoiceService.Instance.GetApprovedInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceController.ApprovedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult RejectedList()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.InvoiceStatus = InvoiceStatus.R;
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult RejectedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.Auditor = LoginHelper.GetUserName();

                var result = new BizInvoiceSearchResultInfo();

                result.InvoiceList = InvoiceService.Instance.GetRejectedInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("InvoiceController.RejectedList", ex);
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
        public ActionResult InvoiceAudit(AuditModel model)
        {
            var invoice = InvoiceService.Instance.GetInvoice(model.InvoiceId);
            var flowAudits = InvoiceAuditService.Instance.GetInvoiceAuditList(model.InvoiceId);

            model.InvoiceAudit = flowAudits.FirstOrDefault(f => f.AuditId == model.AuditId);
                
            if (model.InvoiceAudit == null)
            {
                throw new ApplicationException("未找到审批信息.");
            }

            model.AuditId = model.InvoiceAudit.AuditId;

            return PartialView("InvoiceAudit", model);
        }

        [HttpPost]
        public ActionResult InvoiceAuditList(AuditListModel model)
        {
            var auditListModel = new AuditListModel();

            auditListModel.InvoiceAuditList =
                InvoiceAuditService.Instance.GetInvoiceAuditList(model.InvoiceId);

            return PartialView("InvoiceAuditList", auditListModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InvoiceAuditCreate(AuditModel model)
        {
            var response = new PostResponse();

            bool result = InvoiceService.Instance.Audit(model.InvoiceAudit);

            if (result)
            {
                response.Message = "审核成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "审核失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        
    }
}
