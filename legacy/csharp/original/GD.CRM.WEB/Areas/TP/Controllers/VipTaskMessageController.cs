using System;
using System.Web.Mvc;
using System.Collections.Generic;

using Dchien.ServiceStack.Common.Extensions;
using Dchien.ServiceStack.Text;
using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.TP.ViewModels.Task;

namespace Dchien.Legal.Web.Areas.TP.Controllers
{
    [CheckUserLogin]
    public class VipTaskMessageController : Controller
    {
        internal Log Logger = new Log("TP.Controllers.VipTaskMessageController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult TaskMeesages(string taskGuid)
        {
            var model = new TaskMessageListModel();
            model.Messages = TaskService.Instance.GetTaskMessageList(taskGuid);
            return PartialView("TaskMessages", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="taskId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult TaskNewMeesages(string taskGuid)
        {
            var response = new PostResponse();

            try
            {
                var list = TaskService.Instance.GetTaskMessageList(taskGuid);
                response.IsSuccess = true;
                response.Data = list;
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
        /// <param name="taskId"></param>
        /// <param name="message"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult TaskMessageCreate(string taskGuid, string nodeGuid, string messageGuid,string content)
        {
            var response = new PostResponse();

            var message = new BizModel.TP.Task.BizTaskMessage();

            message.TaskGuid = taskGuid;
            message.NodeGuid = nodeGuid;
            message.MessageGuid = messageGuid;
            message.MessageTypeId = (int)Dchien.Legal.Entity.TP.Task.TaskMessageType.MessageType_100100111;
            message.MessageTypeName = Dchien.Legal.Entity.TP.Task.TaskMessageType.MessageType_100100111.ToDescription();
            message.SendTime = DateTime.Now;
            message.Content = content;

            TaskService.Instance.TaskMessageCreate(message);

            response.Data = new { MessageGuid = Guid.NewGuid()};
            response.IsSuccess = true;

            return Json(response);
        }


        [HttpPost]
        [CheckUserLogin]
        public JsonResult TaskMeesageMarkRead(string taskGuid,string messageGuid)
        {
            var response = new PostResponse();
            var result = TaskService.Instance.TaskMeesageMarkRead(taskGuid, messageGuid);
            response.IsSuccess = result;
          
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult TaskMeesageMarkUnRead(string taskGuid, string messageGuid)
        {
            var response = new PostResponse();
            var result = TaskService.Instance.TaskMeesageMarkUnRead(taskGuid, messageGuid);
            response.IsSuccess = result;

            return Json(response);
        }

    }
}
