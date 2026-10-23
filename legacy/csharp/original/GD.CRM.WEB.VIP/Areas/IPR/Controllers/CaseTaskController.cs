using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.TP;
using Dchien.Legal.Service.TP;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseTaskController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseTaskController");

        [HttpPost]
        public JsonResult Finished(long[] caseIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.TaskService.Instance.TaskFinished(caseIds.ToList());


                if (result)
                {
                    response.Message = "标记成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "标记失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        public ActionResult CaseTaskList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseTaskListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            if (caseId > 0)
            {
                caseModel.CaseTasks = TaskService.Instance.GetTaskList(caseId);
                caseModel.TotalCount = caseModel.CaseTasks.Count;
                caseModel.CaseTasks = caseModel.CaseTasks.Any()
                    ? caseModel.CaseTasks.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .OrderByDescending(x => x.TaskEndTime)
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
                caseModel.CaseTask.TaskPriority = Entity.TP.TaskPriority.Top1;
                caseModel.CaseTask.TaskBeginTime = DateTime.Now;
                caseModel.CaseTask.TaskEndTime = DateTime.Now.AddDays(1);
            }

            return PartialView("CaseTask", caseModel);
        }

        public ActionResult CaseTaskProcess(long taskId)
        {
            var caseModel = new CaseTaskModel();
    
            caseModel.CaseTask = TaskService.Instance.GetTask(taskId);
           
            return PartialView("CaseTaskProcess", caseModel);
        }


        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseTaskCreate(CaseTaskModel model)
        {
            var response = new PostResponse();

            TaskService.Instance.TaskCreateUpdate(model.CaseTask);

            response.Data = "";
            response.IsSuccess = true;

            return Json(response);
        }
    }
}
