using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.FCM.Contract.Audit;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FCM.Contract.Audit;
using Dchien.Legal.Web.Areas.FCM.ViewModels.ContractAudit;
 
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractAuditController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001003)]
        public ActionResult ApprovedList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001003)]
        public ActionResult PendingList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }

        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001003)]
        public ActionResult RejectedList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.AuditStatus = AuditStatus.P;
                model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetPendingContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.PendingList","ContractController.PendingList", ex);
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
        public JsonResult RejectedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ContractStatus = ContractStatus.R;

                model.SearchCondition.AuditStatus = AuditStatus.R;
                model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetRejectedContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractController.RejectedList", "ContractController.RejectedList", ex);
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
        public JsonResult ApprovedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ContractStatus = ContractStatus.A;

                model.SearchCondition.AuditStatus = AuditStatus.A;
                model.SearchCondition.CurrentAuditor = LoginHelper.GetUserName();

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetApprovedContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.ApprovedList","ContractController.ApprovedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
       [CheckUserLogin]
        public ActionResult Audit(long contractId)
        {
            var model = new AuditModel();
            model.ContractId = contractId;

            model.Contract = ContractService.Instance.GetContractById(contractId);

            var flowAudits = ContractAuditService.Instance.GetContractAuditList(contractId);

            model.ContractAudit = flowAudits.FirstOrDefault(f => f.AuditRoundId == model.Contract.ContractBasicInfo.AuditRoundId
                                                    && f.AuditFlowNodeId == model.Contract.ContractBasicInfo.AuditFlowNodeId
                                                    && f.AuditFlowId == model.Contract.ContractBasicInfo.AuditFlowId);

            return View("Audit", model);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult ContractAuditList(AuditListModel model)
        {
            var auditListModel = new AuditListModel();

            auditListModel.ContractAuditList =
                ContractAuditService.Instance.GetContractAuditList(model.ContractId);

            return PartialView("ContractAuditList", auditListModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ContractAuditCreate(AuditModel model)
        {
            var response = new PostResponse();

            bool result = ContractService.Instance.Audit(model.ContractAudit);

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
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ViewContractAuditList()
        {
            var model = new ContractAuditListModel();

            return PartialView("View/ContractAuditList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult ContractAudits(long contractId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var audits = ContractAuditService.Instance.GetContractAuditList(contractId);

            response.Data = audits;

            return Json(response);
        }
    }
}
