using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.Service;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseEventController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseEventController");


        /// <summary>
        /// 打开案件日志
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEvent(CaseEventModel model)
        {
            if (model.EventId.HasValue && model.EventId > 0)
            {
                model.CaseEvent = CaseEventService.Instance.GetCaseEvent(model.EventId.Value);
                return PartialView("CaseEvent", model);
            }
            else
            {
                var c = CaseService.Instance.GetCaseBasic(model.CaseId);
                model.CaseEvent = new BizCaseEvent();
                model.CaseEvent.Deadline = c.CaseBasicInfo.Deadline;
                model.CaseEvent.EventTime = c.CaseBasicInfo.ReminderDate;
                return PartialView("CaseEvent", model);
            }
        }

        public JsonResult CaseEventCreate(CaseEventModel model)
        {
            var response = new PostResponse();
            var c = CaseService.Instance.GetCaseBasic(model.CaseId);

            var caseEvent = new BizCaseEvent();
            caseEvent.CaseId = model.CaseId;
            caseEvent.CaseNo = c.CaseBasicInfo.CaseNo;
            caseEvent.CompanyId = model.CompanyId;
            caseEvent.FileId = 0;
            caseEvent.EventTypeId = 0;
            caseEvent.Deadline = model.CaseEvent.Deadline;
            caseEvent.EventTime = model.CaseEvent.EventTime;
            caseEvent.EventContent = model.CaseEvent.EventContent;

            bool result = CaseEventService.Instance.CreateCaseEvent(caseEvent);

            if (result)
            {
                response.Message = "保存成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "保存失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEventList(long caseId)
        {
            var caseModel = new CaseEventListModel();
            if (caseId > 0)
            {
                caseModel.CaseEvents = CaseEventService.Instance.GetCaseEvents(caseId);
            }
            return PartialView("CaseEventList", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseEventId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseEventDelete(long caseEventId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseEventService.Instance.CaseEventDelete(caseEventId);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseEventController.CaseEventDelete", "CaseEventController.CaseEventDelete", ex);
                throw;
            }

            return Json(response);
        }

    }
}
