using System;
using System.Web.Mvc;
using System.Collections.Generic;

using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.TP.ViewModels.Task;

namespace Dchien.Legal.Web.Areas.TP.Controllers
{
    [CheckUserLogin]
    public class VipTaskNodeController : Controller
    {
        internal Log Logger = new Log("TP.Controllers.VipTaskNodeController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Create(long? taskId)
        {
            if (taskId.HasValue)
            {
                var model = new TaskModel();
                model.Task = TaskService.Instance.GetTask(taskId.Value);
                model.Task.NodeGuid = Guid.NewGuid().ToString();
                model.Task.MessageGuid = Guid.NewGuid().ToString();
                model.Task.TaskBeginTime = DateTime.Now;
                return PartialView(model);
            }

            throw new ArgumentNullException("无效的任务Id");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <param name="message"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult TaskNodeCreate(TaskNodeModel model)
        {
            var response = new PostResponse();

            //if (model.TaskNode.Officer == LoginHelper.GetUserName())
            //{
            //    response.IsSuccess = false;
            //    response.Message = "负责人不允许选择自己.";
            //    return Json(response);
            //}

            if (model.TaskNode.NodeEndTime < model.TaskNode.NodeBeginTime)
            {
                response.IsSuccess = false;
                response.Message = "任务结束时间应大于任务开始时间.";
                return Json(response);
            }

            TaskNodeService.Instance.Create(model.TaskNode);

            response.Data = "";
            response.IsSuccess = true;

            return Json(response);
        }
 

    }
}
