using System;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CMS.Contract;
using Dchien.Legal.Entity.CMS.Contract.Audit;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CMS.Contract;
using Dchien.Legal.Service.CMS.Contract.Audit;
using Dchien.Legal.Web.Areas.CMS.ViewModels.ContractAudit;
 
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CMS.Controllers
{
    [CheckUserLogin]
    public class ContractAuditController : Controller
    {
        internal Log Logger = new Log("CMS.Controllers.ContractController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractList(int? id)
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ApprovedList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            return View(model);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            return View(model);
        }

        [CheckUserLogin]
        public ActionResult RejectedList()
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
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
                    model.SearchCondition.PageSize = 20;

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
                Logger.Error("ContractController.PendingList", ex);
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
                    model.SearchCondition.PageSize = 20;

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
                Logger.Error("ContractController.RejectedList", ex);
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
                    model.SearchCondition.PageSize = 20;

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
                Logger.Error("ContractController.ApprovedList", ex);
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
        public ActionResult ContractAudit(AuditModel model)
        {
            var contract = ContractService.Instance.GetContractById(model.ContractId);
            var flowAudits = ContractAuditService.Instance.GetContractAuditList(model.ContractId);

            model.ContractAudit =
                flowAudits.FirstOrDefault(f => f.ContractId == contract.ContractBasicInfo.ContractId
                                               && f.AuditRoundId == contract.ContractBasicInfo.AuditRoundId
                                               && f.AuditFlowId == contract.ContractBasicInfo.AuditFlowId
                                               && f.AuditFlowNodeId == contract.ContractBasicInfo.AuditFlowNodeId);

            if (model.ContractAudit == null)
            {
                throw new ApplicationException("未找到审批信息.");
            }

            model.AuditId = model.ContractAudit.AuditId;

            return PartialView("ContractAudit", model);
        }

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
    }
}
