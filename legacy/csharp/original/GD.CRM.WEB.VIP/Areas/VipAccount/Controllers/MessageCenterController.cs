using System;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.Account.Message;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.Account.Message;
using Dchien.Legal.VipWeb.Areas.Account.ViewModels.Message;
using Dchien.Legal.VipWeb.Controllers;
using Dchien.Legal.VipWeb.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.HR.Staff;

namespace Dchien.Legal.VipWeb.Areas.VipAccount.Controllers
{
    [CheckVipUserLogin]
    public class MessageCenterController : Controller
    {
        internal Log Logger = new Log("Account.Controllers.MessageCenterController");

        [HttpPost]
        public ActionResult Messages(string id)
        {
            var response = new PostResponse();

            var result = new BizMessageSearchResultInfo();

            var searchCondition = new MessageSearchCondition();
            searchCondition.PageNo = 1;
            searchCondition.PageSize = 5;
            searchCondition.MessageTypeId = 1;
            result.Messages = Dchien.Legal.Service.MessageService.Instance.GetMessages(searchCondition);

            result.TotalItemCount = searchCondition.TotalCount;
            result.PageNo = searchCondition.PageNo;
            result.PageSize = searchCondition.PageSize;
            response.IsSuccess = true;

            response.Data = result;

            return Json(response);
        }



        [HttpGet]
        public ActionResult Index(int? typeId)
        {
            ViewBag.BodyClass = "message-center";
            var model = new MessageListModel();
            model.MessageTypeId = typeId;
            return View(model);
        }

        [HttpPost]
        public JsonResult List(MessageListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.MessageTypeId = model.MessageTypeId;

                var result = new BizMessageSearchResultInfo();

                result.Messages = MessageService.Instance.GetMessages(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;

                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "MessageCenterController.List", "MessageCenterController.List", ex);
                response.IsSuccess = false;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult Message(long? id = 0)
        {
            var model = new MessageModel();

            var staffs = StaffService.Instance.GetStaffList();

            if (id.HasValue && id.Value > 0)
            {
                model.Message = MessageService.Instance.GetMessage(id.Value);
                model.Message.ReceiverName = staffs.FirstOrDefault(x => x.StaffBasic.StaffName == model.Message.Receiver) == null
                    ? string.Empty
                    : staffs.FirstOrDefault(x => x.StaffBasic.StaffName == model.Message.Receiver).StaffBasic.StaffChName;

                model.Message.SenderName = staffs.FirstOrDefault(x => x.StaffBasic.StaffName == model.Message.Sender) == null
                    ? string.Empty
                    : staffs.FirstOrDefault(x => x.StaffBasic.StaffName == model.Message.Sender).StaffBasic.StaffChName;
            }
            else
            {
                model.Message = new BizMessage();
            }

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult MarkRead(long messageId)
        {
            var response = new PostResponse();
            bool result = MessageService.Instance.MarkRead(messageId);
            if (result)
            {
                response.IsSuccess = true;
                response.Message = "标记阅读成功.";
            }
            else
            {
                response.IsSuccess = false;
                response.Message = "标记阅读失败.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Send(MessageModel model)
        {
            var response = new PostResponse();

            bool result = MessageService.Instance.CreateUpdate(model.Message);

            if (result)
            {
                response.IsSuccess = true;
                response.Message = "发送成功.";
            }
            else
            {
                response.IsSuccess = false;
                response.Message = "发送失败.";
            }

            return Json(response);
        }
    }
}