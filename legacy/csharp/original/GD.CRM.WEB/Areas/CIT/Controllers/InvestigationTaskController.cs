using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.ServiceStack.Common.Extensions;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationTask;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.HR.Staff;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Task;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationTaskController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationTaskController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="investigationNo"></param>
        /// <returns></returns>
        public ActionResult Create(string id,string investigationNo)
        {
            var model = new InvestigationTaskModel();

            var investigation = InvestigationService.Instance.GetInvestigation(investigationNo);

            if (investigation == null)
            {
                throw new Exception("未找到调查任务.");
            }

            model.Investigation = investigation;
            model.InvestigationTask = new BizInvestigationTask();
            model.InvestigationTask.Basic = new BizInvestigationTaskBasic();
            model.InvestigationTask.Basic.InvestigationNo = investigationNo;
            model.InvestigationTask.Basic.BeginTime = investigation.Basic.AuthorizationBeginTime;
            model.InvestigationTask.Basic.EndTime = investigation.Basic.AuthorizationEndTime;

            return View("Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult CreateUpdate(InvestigationTaskModel model)
        {
            var response = new PostResponse();

            model.InvestigationTask.Basic.Investigator.Split(';').ToList().ForEach(x =>
            {
                model.InvestigationTask.Basic.BusinessOwner = LoginHelper.GetUserName();

                var task = model.InvestigationTask.TranslateTo<BizInvestigationTask>();
                task.Basic.Investigator = x;
                task.Basic.InvestigatorName = StaffService.Instance.GetStaffByUserName(x).UserChName;
                InvestigationTaskService.Instance.CreateUpdate(task);

            });
               
            response.Message = "分配成功！";
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string id)
        {
            var model = new InvestigationTaskListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult List(InvestigationTaskListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvestigationTaskSearchResultInfo();

                if (model.SearchCondition.PageId == PageId.PageId_1401005)
                {
                    model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else
                {
                    model.SearchCondition.Investigator = LoginHelper.GetUserName();
                    model.SearchCondition.CheckTaskExpiryTime = true;
                }


                result.InvestigationTasks = InvestigationTaskService.Instance.GetInvestigationTaskList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult TaskList()
        {
            var model = new InvestigationTaskListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            return PartialView("PartialView/TaskList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult InvestigationTasks(string investigationNo, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationTasks = new List<BizInvestigationTask>();

            if (!string.IsNullOrEmpty(investigationNo))
            {
                investigationTasks = InvestigationTaskService.Instance.GetInvestigationTaskList(investigationNo);
            }

            var result = new BizInvestigationTaskSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationTasks.Count;

            result.InvestigationTasks = investigationTasks.Any()
                    ? investigationTasks.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.Basic.TaskId)
                        .ToList()
                    : new List<BizInvestigationTask>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskNos"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Delete(List<string> taskNos)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvestigationTaskService.Instance.Delete(taskNos);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationFileController.Delete", "InvestigationFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult PreView(string id, string investigationTaskNo)
        {
            var model = new InvestigationTaskModel();
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(investigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            return PartialView("PartialView/PreView", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Edit(string investigationTaskNo)
        {
            var model = new InvestigationTaskModel();
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(investigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            return PartialView("PartialView/Edit", model);
        }
    }
}
