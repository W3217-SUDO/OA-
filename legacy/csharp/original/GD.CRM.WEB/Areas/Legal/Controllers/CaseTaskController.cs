using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.TP.Task;
using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Entity.Account;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseTaskController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseTaskController");


        [HttpPost]
        public ActionResult CaseTaskList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseTaskListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            caseModel.CaseId = caseId;

            if (caseId > 0)
            {
                caseModel.CaseTasks = TaskService.Instance.GetTaskList(caseId);
                caseModel.TotalCount = caseModel.CaseTasks.Count;
                caseModel.CaseTasks = caseModel.CaseTasks.Any()
                    ? caseModel.CaseTasks.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<BizTask>();
            }

            return PartialView("CaseTaskList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        public ActionResult CaseTask(long? taskId)
        {
            var caseModel = new CaseTaskModel();

            if (taskId.HasValue)
            {
                caseModel.CaseTask = TaskService.Instance.GetTask(taskId.Value);
            }
            else
            {
                caseModel.CaseTask = new BizTask();
                caseModel.CaseTask.TaskPriority = Entity.TP.Task.TaskPriority.Top1;
                caseModel.CaseTask.TaskBeginTime = DateTime.Now;
                caseModel.CaseTask.TaskEndTime = DateTime.Now.AddDays(1);
            }

            return PartialView("CaseTask", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseTaskCreate(CaseTaskModel model)
        {
            var response = new PostResponse();
            TaskService.Instance.TaskCreateUpdate(model.CaseTask);
            response.Message = "";
            response.IsSuccess = true;

            return Json(response);
        }
    }
}
