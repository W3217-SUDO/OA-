using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.Service;
using Dchien.Legal.Common;
using Dchien.Legal.BizModel.Legal.Case; 
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseLogController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseLogController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseLogList(string caseNo)
        {
            var caseModel = new CaseLogListModel();
            if (!string.IsNullOrEmpty(caseNo))
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseNo);
            }
            return PartialView("PartialView/CaseLogList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseOperatingLogList(string caseNo, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseLogListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (!string.IsNullOrEmpty(caseNo))
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseNo);
                caseModel.TotalCount = caseModel.CaseLogs.FindAll(x => x.LogType == (int)CaseLogType.Operation).Count;
                caseModel.CaseLogs = caseModel.CaseLogs.FindAll(x => x.LogType == (int)CaseLogType.Operation).Any()
                    ? caseModel.CaseLogs.FindAll(x => x.LogType == (int)CaseLogType.Operation).Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .OrderByDescending(x => x.OperatorDate)
                        .ToList()
                    : new List<BizCaseLog>();
            }

            return PartialView("PartialView/CaseOperatingLogList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseLog(CaseLogModel model)
        {
            var caseModel = new CaseLogModel();
            if (model.LogId.HasValue && model.LogId > 0)
            {
                caseModel.CaseLog = CaseLogService.Instance.GetCaseLog(model.LogId.Value);
            }
            else
            {
                caseModel.CaseLog = new BizCaseLog();
                caseModel.CaseLog.LogType = (int)CaseLogType.Business;
            }
            return PartialView("PartialView/CaseLog", caseModel);
        }

        [HttpPost]
        public ActionResult CaseLogForCourt(CaseLogModel model)
        {
            var caseModel = new CaseLogModel();
            if (model.LogId.HasValue && model.LogId > 0)
            {
                caseModel.CaseLog = CaseLogService.Instance.GetCaseLog(model.LogId.Value);
            }
            else
            {
                caseModel.CaseLog = new BizCaseLog();
                caseModel.CaseLog.LogType = (int)CaseLogType.Business;
            }
            return PartialView("PartialView/CaseLogForCourt", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseLogCreate(CaseLogModel model)
        {
            var response = new PostResponse();

            if (string.IsNullOrEmpty(model.CaseNos))
            {
                response.Message = "请选择案件.";
                response.IsSuccess = false;
                return Json(response);
            }

            try
            {
                model.CaseNos.Split(',').ToList().ForEach(caseNo =>
                {
                    var caseLog = new BizCaseLog();
                    var c = CaseService.Instance.GetCaseBasic(caseNo);
                    caseLog.CaseId = c.Basic.CaseId;
                    caseLog.CaseNo = c.Basic.CaseNo;
                    caseLog.Content = model.CaseLog.Content;
                    caseLog.LogType = (int)CaseLogType.Business;

                    CaseLogService.Instance.CreateCaseLog(caseLog);
                });

                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseLogController.CaseLogCreate", "CaseLogController.CaseLogCreate", ex);
                response.Message = "保存失败！";
                response.IsSuccess = false;
            }
      
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseLogId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseLogDelete(long caseLogId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseLogService.Instance.CaseLogDelete(caseLogId);

                if (result)
                {
                    response.Message = "删除成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "删除失败！";
                    response.IsSuccess = false;
                }

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseLogController.CaseLogDelete", "CaseLogController.CaseLogDelete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult List(string caseNo)
        {
            var caseModel = new CaseLogListModel();
            if (!string.IsNullOrEmpty(caseNo))
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseNo);
            }
            return PartialView("PartialView/List", caseModel);
        }
    }
}
