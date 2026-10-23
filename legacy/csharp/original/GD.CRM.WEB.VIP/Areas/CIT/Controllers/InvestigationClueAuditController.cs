using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Entity.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Case;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationClueAuditController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueAuditController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList(string id)
        {
            var model = new InvestigationClueListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ApprovedList(string id)
        {
            var model = new InvestigationClueListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>

        [CheckUserLogin]
        public ActionResult RejectedList(string id)
        {
            var model = new InvestigationClueListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationClueNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Audit(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClue(investigationClueNo);
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(model.InvestigationClue.Basic.InvestigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            model.ConflictInvestigationClueNos = InvestigationClueService.Instance.GetConflictInvestigationClueList(model.InvestigationClue);
            model.ConflictCaseNos = InvestigationClueService.Instance.GetConflictCaseList(model.InvestigationClue);

            return PartialView("PartialView/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationClueNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult CustomerAudit(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClue(investigationClueNo);
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(model.InvestigationClue.Basic.InvestigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            model.ConflictInvestigationClueNos = InvestigationClueService.Instance.GetConflictInvestigationClueList(model.InvestigationClue);
            model.ConflictCaseNos = InvestigationClueService.Instance.GetConflictCaseList(model.InvestigationClue);

            return PartialView("PartialView/CustomerAudit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="clueNo"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Approved(string clueNo,string auditRemark,bool auditNeedMergeCase,string auditNeedMergeCaseNo)
        {
            var response = new PostResponse();

            if (auditNeedMergeCase && !string.IsNullOrEmpty(auditNeedMergeCaseNo))
            {
                var c = CaseService.Instance.GetCaseBasic(auditNeedMergeCaseNo);

                if (c == null)
                {
                    response.IsSuccess = true;
                    response.Message = "并入案号未找到，请重新输入.";
                    return Json(response);
                }
            }

            InvestigationClueService.Instance.Audit(clueNo, auditRemark, InvestigationClueStatus.E,auditNeedMergeCase,auditNeedMergeCaseNo);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult CustomerApproved(string clueNo, string auditRemark)
        {
            var response = new PostResponse();
            InvestigationClueService.Instance.CustomerAudit(clueNo, auditRemark, InvestigationClueStatus.E);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="clueNo"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Rejected(string clueNo, string auditRemark, bool auditNeedMergeCase, string auditNeedMergeCaseNo)
        {
            var response = new PostResponse();
            InvestigationClueService.Instance.Audit(clueNo, auditRemark, InvestigationClueStatus.R,auditNeedMergeCase,auditNeedMergeCaseNo);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="clueNo"></param>
        /// <param name="auditRemark"></param>
        /// <param name="auditNeedMergeCase"></param>
        /// <param name="auditNeedMergeCaseNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult CustomerRejected(string clueNo, string auditRemark)
        {
            var response = new PostResponse();
            InvestigationClueService.Instance.CustomerAudit(clueNo, auditRemark, InvestigationClueStatus.R);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationClueNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult ToAudit(string id, List<string> clueNos)
        {
            var response = new PostResponse();

            clueNos.ForEach(x =>
            {
                InvestigationClueService.Instance.ToAudit(x);
            });

            response.IsSuccess = true;
            response.Message = "提交成功.";
            return Json(response);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult TrunOnToAudit(string id, string investigationClueNo,string trunOnToAuditor)
        {
            var response = new PostResponse();
            InvestigationClueService.Instance.TrunOnToAudit(investigationClueNo, trunOnToAuditor);
            response.IsSuccess = true;
            response.Message = "提交成功.";
            return Json(response);
        }
    }
}
