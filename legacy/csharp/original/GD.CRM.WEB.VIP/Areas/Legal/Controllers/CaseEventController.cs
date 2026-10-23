using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.Service;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseEvent;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseEventController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseEventController");


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
            return PartialView("PartialView/CaseEventList", caseModel);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEvent(CaseEventModel model)
        {
            if (model.EventId.HasValue && model.EventId > 0)
            {
                //model.CaseEvent = CaseEventService.Instance.GetCaseEvent(model.EventId.Value);
                return PartialView("PartialView/CaseEvent", model);
            }
            else
            {
                var c = CaseService.Instance.GetCaseBasic(model.CaseNo);
                model.CaseEvent = new BizCaseEvent();
                model.CaseEvent.Deadline = c.Basic.Deadline;
                return PartialView("PartialView/CaseEvent", model);
            }

        }

        [HttpPost]
        public JsonResult CaseEventCreate(CaseEventModel model)
        {
            var response = new PostResponse();
            var c = CaseService.Instance.GetCaseBasic(model.CaseNo);

            var caseEvent = new BizCaseEvent();
            caseEvent.CaseId = c.Basic.CaseId;
            caseEvent.CaseNo = c.Basic.CaseNo;
            caseEvent.CompanyId = c.Basic.CompanyId;
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

        //[HttpPost]
        //public JsonResult CaseEventCreate(Dchien.Legal.Web.Areas.Legal.ViewModels.CaseEvent.CaseEventModel model)
        //{
        //    var response = new PostResponse();
        //    //var caseList = CaseService.Instance.GetCaseBasic(model.CaseIds);
        //    //var caseEvents = new List<BizCaseEvent>();

        //    //caseList.ForEach(c =>
        //    //{
        //    //    var caseEvent = new BizCaseEvent();
        //    //    caseEvent.CaseId = c.CaseBasicInfo.CaseId;
        //    //    caseEvent.CaseNo = c.CaseBasicInfo.CaseNo;
        //    //    caseEvent.CompanyId = c.CaseBasicInfo.CompanyId;
        //    //    caseEvent.EventTypeId = (int)CaseEventType.EventType0;
        //    //    caseEvent.Deadline = model.EventTime;
        //    //    caseEvent.EventTime = model.EventTime;
        //    //    caseEvent.EventContent = model.EventContent;

        //    //     CaseEventService.Instance.CreateCaseEvent(caseEvent);
        //    // });

        //    //response.Message = "保存成功！";
        //    //response.IsSuccess = true;

        //    return Json(response);
        //}


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseEventRemove(List<long> caseIds)
        {
            var response = new PostResponse();

            CaseEventService.Instance.CaseEventDelete(caseIds);

            response.Message = "删除成功！";
            response.IsSuccess = true;

            return Json(response);
        }

    }
}
