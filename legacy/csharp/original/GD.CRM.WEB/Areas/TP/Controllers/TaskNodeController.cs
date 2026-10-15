using System;
using System.Web.Mvc;
using System.Collections.Generic;
using System.Linq;

using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.TP.ViewModels.Task;
using Dchien.Legal.Service.HR.Staff;

namespace Dchien.Legal.Web.Areas.TP.Controllers
{
    [CheckUserLogin]
    public class TaskNodeController : Controller
    {
        internal Log Logger = new Log("TP.Controllers.TaskNodeController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
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
        /// <param name="taskIds"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult MultipleCreate()
        {
            var model = new TaskModel();
            model.Task = new BizModel.TP.Task.BizTask();
            model.Task.TaskGuid = Guid.NewGuid().ToString();
            model.Task.NodeGuid = Guid.NewGuid().ToString();
            model.Task.MessageGuid = Guid.NewGuid().ToString();
            model.Task.TaskBeginTime = DateTime.Now;
            return PartialView(model);
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

            if (StaffService.Instance.GetStaffByUserName(model.TaskNode.Officer) == null)
            {
                response.IsSuccess = false;
                response.Message = "请输入负责人.";
                return Json(response);
            }

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult MultipleTaskNodeCreate(TaskNodeModel model)
        {
            var response = new PostResponse();

            if (StaffService.Instance.GetStaffByUserName(model.TaskNode.Officer) == null)
            {
                response.IsSuccess = false;
                response.Message = "请输入负责人.";
                return Json(response);
            }

            if (model.TaskNode.NodeEndTime < model.TaskNode.NodeBeginTime)
            {
                response.IsSuccess = false;
                response.Message = "任务结束时间应大于任务开始时间.";
                return Json(response);
            }

            if (string.IsNullOrEmpty(model.TaskIds))
            {
                response.IsSuccess = false;
                response.Message = "请选择任务.";
                return Json(response);
            }

            var result = TaskNodeService.Instance.MultipleCreate(model.TaskIds.Split<long>(',').ToList<long>() ,model.TaskNode);

            response.Data = "";
            response.IsSuccess = true;

            return Json(response);
        }


    }
}
