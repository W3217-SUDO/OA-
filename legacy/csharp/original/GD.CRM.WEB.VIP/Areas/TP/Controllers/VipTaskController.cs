using System;
using System.Web.Mvc;
using System.Collections.Generic;
using System.Linq;

using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.TP.ViewModels.Task;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.TP.Controllers
{
    [CheckUserLogin]
    public class VipTaskController : Controller
    {
        internal Log Logger = new Log("TP.Controllers.VipTaskController");

        [CheckUserLogin]
        public ActionResult TaskList(string id,long? taskId)
        {
            var model = new ListModel();
            model.SearchCondition.PageId = id;
            model.TaskId = taskId;

            if (model.SearchCondition.PageId == PageId.PageId_9001001010)
            {
                model.SearchCondition.TaskStatus = TaskStatus.Processing;
                model.SearchCondition.Initiator = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_9001001020)
            {
                model.SearchCondition.NodeStatus = NodeStatus.Pending;
                model.SearchCondition.Officer = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_9001001030)
            {
                model.SearchCondition.NodeStatus = NodeStatus.Processing;
                model.SearchCondition.Participant = LoginHelper.GetUserName();
            }

            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View(model);
        }
 

        [CheckUserLogin]
        public ActionResult TaskDetail(long? taskId)
        {
            if (taskId.HasValue)
            {
                var model = new TaskModel();
                model.Task = TaskService.Instance.GetTask(taskId.Value);
                model.TaskNode = TaskNodeService.Instance.GetTaskNode(model.Task.NodeGuid);
                model.Task.MessageGuid = Guid.NewGuid().ToString();
                return PartialView(model);
            }

            throw new ArgumentNullException("无效的任务Id");
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult TaskSearchList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new Dchien.Legal.BizModel.TP.Task.BizTaskSearchResultInfo();

                result.TaskList = TaskService.Instance.GetTaskList(model.SearchCondition);

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

        [CheckUserLogin]
        public ActionResult Create(long id,string caseNos)
        {
            var model = new TaskModel();
            model.Task = new BizModel.TP.Task.BizTask();
            model.Task.TaskGuid = Guid.NewGuid().ToString();
            model.Task.NodeGuid = Guid.NewGuid().ToString();
            model.Task.MessageGuid = Guid.NewGuid().ToString();
            model.Task.TaskBeginTime = DateTime.Now;
            model.CaseNos = caseNos;

            return View(model);
        }

        [CheckUserLogin]
        [HttpPost]
        public ActionResult TaskCreate(string caseNos)
        {
            var model = new TaskModel();
            model.Task = new BizModel.TP.Task.BizTask();
            model.Task.TaskGuid = Guid.NewGuid().ToString();
            model.Task.NodeGuid = Guid.NewGuid().ToString();
            model.Task.MessageGuid = Guid.NewGuid().ToString();

            model.CaseNos = caseNos;

            return PartialView(model);
        }

        [HttpPost]
        [CheckUserLogin]
        public ActionResult CreateUpdate(TaskModel model)
        {
            var response = new PostResponse();

            //if (model.Task.Officer == LoginHelper.GetUserName())
            //{
            //    response.IsSuccess = false;
            //    response.Message = "负责人不允许选择自己.";
            //    return Json(response);
            //}

            if (model.Task.TaskEndTime < model.Task.TaskBeginTime)
            {
                response.IsSuccess = false;
                response.Message = "任务结束时间应大于任务开始时间.";
                return Json(response);
            }

            if (!string.IsNullOrEmpty(model.CaseNos))
            {
                try
                {
                    model.CaseNos.Split(',').ToList().ForEach(caseNo =>
                    {
                        var task = model.Task;
                        task.CaseNo = caseNo;

                        TaskService.Instance.Create(task);
                    });
                }
                catch
                {
                    response.IsSuccess = false;
                    response.Message = "发布任务失败.";
                    return Json(response);
                }
            }
 
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Checked(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.Checked(taskIds[0]);

                if (result)
                {
                    response.Message = "任务结束成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务结束失败！";
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Finished(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.Finished(taskIds[0]);

                if (result)
                {
                    response.Message = "任务结束成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务结束失败！";
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Rejected(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.Rejected(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务拒绝成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务拒绝失败！";
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Stoped(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.Stoped(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务停止成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务停止失败！";
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
        public JsonResult ReOpen(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.ReOpen(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务拒绝成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务拒绝失败！";
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
        public JsonResult TaskDelete(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.TaskDelete(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务删除成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务删除失败！";
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
        public JsonResult Process(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.Process(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务进行中";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务处理异常！";
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
        public JsonResult Delete(long[] taskIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = Dchien.Legal.Service.TP.Task.TaskService.Instance.TaskDelete(taskIds.ToList());

                if (result)
                {
                    response.Message = "任务删除成功";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "任务删除异常！";
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
        [CheckUserLogin]
        public JsonResult GetNewMessageTasks()
        {
            var response = new PostResponse();

            try
            {

                var searchCondition = new TaskSearchCondition();
                searchCondition.PageSize = 10000;
                searchCondition.PageNo = 1;
                searchCondition.PageId = PageId.PageId_9001001100;

                var result = new Dchien.Legal.BizModel.TP.Task.BizTaskSearchResultInfo();

                result.TaskList = TaskService.Instance.GetTaskList(searchCondition);

                result.TotalItemCount = result.TaskList.Count;
                result.PageNo = searchCondition.PageNo;
                result.PageSize = searchCondition.PageSize;

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


        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetTaskNotificationMessages()
        {
            var response = new PostResponse();

            try
            {
                var taskNotificationMessages = TaskService.Instance.GetTaskNotificationMessages(LoginHelper.GetUserName());

                response.IsSuccess = true;
                response.Data = new { TaskNotificationMessages = taskNotificationMessages };
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }
        

    }
}
