using System;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.AP.CaseFee;
using Dchien.Legal.BizModel.FAM.AP.CaseFee.Application;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.Account;
using Dchien.Legal.Entity.FAM.AP;
using Dchien.Legal.Entity.FAM.AP.CaseFee;
using Dchien.Legal.Entity.FAM.AP.CaseFee.Application;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAM.AP.CaseFee;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Audit;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class APController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.APController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList()
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new APSearchCondition(); 
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.P;
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

                model.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.P;
                model.SearchCondition.Auditor = LoginHelper.GetUserName();

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = CaseFeeService.Instance.GetPendingCaseFeeList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("APController.PendingList", ex);
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
            listModel.SearchCondition = new APSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.R;
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

                model.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.R;
                if (LoginHelper.GetAccesslevel() != (int)AccessLevel.All)
                {
                    model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = CaseFeeService.Instance.GetRejectedCaseFeeList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("APController.RejectedList", ex);
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
            listModel.SearchCondition = new APSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 20;
            listModel.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.A;
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

                model.SearchCondition.ApplicationStatus = CaseFeeApplicationStatus.A;

                if (LoginHelper.GetAccesslevel() != (int) AccessLevel.All)
                {
                    model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = CaseFeeService.Instance.GetApprovedCaseFeeList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("APController.ApprovedList", ex);
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
        public ActionResult CaseFeeApplicationAudit(Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Audit.AuditModel model)
        {
            var audit = CaseFeeApplicationAuditService.Instance.GetCaseFeeApplicationAuditById(model.AuditId);
            model.Audit = audit;

            return PartialView("Audit/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFeeApplicationAuditCreate(Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Audit.AuditModel model)
        {
            var response = new PostResponse();

            bool result = CaseFeeApplicationService.Instance.Audit(model.Audit);

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeApplicationAuditList(AuditListModel model)
        {
            var auditListModel = new AuditListModel();

            auditListModel.AuditList =
                CaseFeeApplicationAuditService.Instance.GetCaseFeeApplicationAuditList(model.ApplicationId);

            return PartialView("Audit/AuditList", auditListModel);
        }

    }
}
