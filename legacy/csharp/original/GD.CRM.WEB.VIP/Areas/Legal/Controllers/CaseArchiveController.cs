using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.ServiceStack.Common.Extensions;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseList;
using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseArchiveController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseArchiveController");

        /// <summary>
        /// 新建内部费用
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ApplicationCreate(int archiveTypeId)
        {
            ViewBag.ArchiveTypeId = archiveTypeId;
            return PartialView("PartialView/ApplicationCreate");
        }

        [HttpPost]
        public ActionResult Audit()
        {
            return PartialView("PartialView/Audit");
        }
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult ToAudit(CaseArchiveModel model)
        {
            var response = new PostResponse();
            try
            {
                var messages = new List<string>();

                model.Cases.ForEach(x =>
                {
                    x.Basic.ArchiveTypeId = (CaseArchiveType)model.CaseArchiveTypeId;

                    if (x.Basic.ArchiveTypeId == CaseArchiveType.Normal && !CaseArchiveAuditService.Instance.CheckAllCaseFeeCashed(x))
                    {
                        messages.Add(string.Format("{0}案件费用未到账,不允许提交归档审核.",x.Basic.CaseNo));
                    }
                    else
                    {
                        CaseArchiveAuditService.Instance.ToAudit(x);
                    }
                });

                if (messages.Any())
                {
                    response.Message = string.Join("<br>",messages);
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "已申请归档,待审核.";
                    response.IsSuccess = true;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseArchiveController.ToAudit", "CaseArchiveController.ToAudit", ex);
                response.IsSuccess = false;
                response.Message = "提交出错.";
            }
            return Json(response);
 
        }

        /// <summary>
        /// 
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Approved(CaseArchiveModel model)
        {
            var response = new PostResponse();
            try
            {
                model.Cases.ForEach(x =>
                {
                    CaseArchiveAuditService.Instance.Approved(x);
                });
                response.Message = "审核成功.";
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseArchiveController.Approved", "CaseArchiveController.Approved", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Rejected(CaseArchiveModel model)
        {
            var response = new PostResponse();
            try
            {
                model.Cases.ForEach(x =>
                {
                    CaseArchiveAuditService.Instance.Rejected(x);
                });
                response.Message = "拒绝成功.";
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseArchiveController.Rejected", "CaseArchiveController.Rejected", ex);
                response.IsSuccess = false;
                response.Message = "拒绝出错.";
            }
            return Json(response);
        }

        /// <summary>
        ///  
        /// </summary>
        /// <param name="id"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        public ActionResult PendingList(string id, string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            //model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
            model.SearchCondition.Keyword = k;
            model.SearchCondition.Sorting = "T.ToAuditTime";

            // 待审核
            var casePhases = new List<int>();
            var casePhaseNames = new List<string>();
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106011);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106011.ToDescription());
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106017);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106017.ToDescription());
            model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
            model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }

        /// <summary>
        ///  
        /// </summary>
        /// <param name="id"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        public ActionResult ApprovedList(string id, string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            //model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
            model.SearchCondition.Keyword = k;
            model.SearchCondition.Sorting = "T.AuditedTime desc";

            // 已归档
            var casePhases = new List<int>();
            var casePhaseNames = new List<string>();
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106012);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106012.ToDescription());
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106018);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106018.ToDescription());
            model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
            model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        public ActionResult RejectedList(string id, string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
            model.SearchCondition.Keyword = k;
            model.SearchCondition.Sorting = "T.AuditedTime desc";

            // 已拒绝
            var casePhases = new List<int>();
            var casePhaseNames = new List<string>();
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106014);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106014.ToDescription());
            casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106019);
            casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_106019.ToDescription());
            model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
            model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }
    }
}
