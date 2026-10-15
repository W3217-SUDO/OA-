using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument;
using Dchien.Legal.Service.AWS.OfficialDocument;
using Dchien.Legal.Entity.AWS.OfficialDocument;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentAudit;
using Dchien.Legal.Service.AWS.OfficialDocument.Audit;

namespace Dchien.Legal.Web.Areas.AWS.Controllers
{
    [CheckUserLogin]
    public class OfficialDocumentAuditController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.OfficialDocumentAuditController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PendingList(string id)
        {
            var model = new OfficialDocumentListModel();
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
            var model = new OfficialDocumentListModel();
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
            var model = new OfficialDocumentListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Audit(string id, string officialDocumentNo)
        {
            var model = new AuditModel();

            model.OfficialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
            var flowAudits = OfficialDocumentAuditService.Instance.GetOfficialDocumentAuditList(officialDocumentNo);
            model.OfficialDocumentAudit = flowAudits.FirstOrDefault(f => f.AuditRoundId == model.OfficialDocument.Basic.AuditRoundId
                                        && f.AuditFlowNodeId == model.OfficialDocument.Basic.AuditFlowNodeId
                                        && f.AuditFlowId == model.OfficialDocument.Basic.AuditFlowId);

            return PartialView("PartialView/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        public ActionResult AuditList(string id, string officialDocumentNo)
        {
            var model = new AuditListModel();
            model.OfficialDocumentAuditList = OfficialDocumentAuditService.Instance.GetOfficialDocumentAuditList(officialDocumentNo);
            return PartialView("PartialView/AuditList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNo"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Approved(long auditId,string officialDocumentNo, string auditRemark)
        {
            var response = new PostResponse();

            var audit = new BizModel.AWS.OfficialDocument.BizOfficialDocumentAudit();
            audit.AuditId = auditId;
            audit.AuditContent = auditRemark;
            audit.OfficialDocumentNo = officialDocumentNo;
            audit.AuditStatus = Entity.System.AuditStatus.A;

            OfficialDocumentService.Instance.Audit(audit);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="auditId"></param>
        /// <param name="officialDocumentNo"></param>
        /// <param name="auditRemark"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Rejected(long auditId, string officialDocumentNo, string auditRemark)
        {
            var response = new PostResponse();

            var audit = new BizModel.AWS.OfficialDocument.BizOfficialDocumentAudit();
            audit.AuditId = auditId;
            audit.AuditContent = auditRemark;
            audit.OfficialDocumentNo = officialDocumentNo;
            audit.AuditStatus = Entity.System.AuditStatus.R;

            OfficialDocumentService.Instance.Audit(audit);
            response.IsSuccess = true;
            response.Message = "审批成功.";
            return Json(response);
        }
    }
}
