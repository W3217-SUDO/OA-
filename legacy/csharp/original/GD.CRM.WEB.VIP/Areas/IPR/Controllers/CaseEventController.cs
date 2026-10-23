using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Service.IPR.CaseFileProcess;
using Dchien.Legal.Web.Areas.IPR.Controllers;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseEventController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseEventController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseEventNotIn(long caseId, string caseNo)
        {
            var model = new CaseEventNotInModel();
            model.CaseId = caseId;
            model.CaseNo = caseNo;

            model.CaseEventTypes = new List<BizCaseEventType>();
            model.CaseEventTypes.Add(new BizCaseEventType() {EventTypeId = 1, EventTypeName = "申请费"});
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 2, EventTypeName = "提实质审查缴纳实质审查费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 3, EventTypeName = "缴纳登记、印刷费、印花税、首年年费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 4, EventTypeName = "缴纳年费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 5, EventTypeName = "缴纳滞纳金及年费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 6, EventTypeName = "缴纳优先权费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 7, EventTypeName = "补充优先权证明文本" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 8, EventTypeName = "专利补正" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 9, EventTypeName = "提出复审缴纳复审费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 10, EventTypeName = "缴纳著入项目变更费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 11, EventTypeName = "专利补充证据材料" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 12, EventTypeName = "商标提出复审" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 13, EventTypeName = "商标补正" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 14, EventTypeName = "商标补充证据材料" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 15, EventTypeName = "商标续展" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 16, EventTypeName = "商标初审公布" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 17, EventTypeName = "著作权补正" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 18, EventTypeName = "缴纳无效申请费" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 19, EventTypeName = "答复审查意见" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 20, EventTypeName = "第N次答复审查意见" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 23, EventTypeName = "商标异议答辩" });
            model.CaseEventTypes.Add(new BizCaseEventType() { EventTypeId = 24, EventTypeName = "办理专利资助" });

            model.EventTypeIds = CaseEventService.Instance.GetCaseEventTypeNotIn(caseId);

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseNo"></param>
        /// <param name="caseEventTypeIds"></param>
        /// <returns></returns>
        //[HttpPost]
        //[CheckUserLogin]
        //public ActionResult CaseEventNotInCreate(long caseId, string caseNo, int[] caseEventTypeIds)
        //{
        //    var response = new PostResponse();
        //    CaseEventService.Instance.CaseEventNotInCreate(caseId, caseNo, caseEventTypeIds.ToList());

        //    response.Data = "";
        //    response.IsSuccess = true;
        //    return Json(response);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult CaseEventNotInCreate(CaseEventNotInModel model)
        {
            var response = new PostResponse();
            CaseEventService.Instance.CaseEventNotInCreate(model.CaseId, model.CaseNo, model.EventTypeIds);

            response.Data = "";
            response.IsSuccess = true;
            return Json(response);
        }


        /// <summary>
        /// type=1 表示我的案件
        /// type=2 表示提醒案件
        /// type=3 未申请案件
        /// </summary>
        /// <param name="typeId"></param>
        /// <param name="caseId"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CreateUpdate(int? typeId = 1, long? caseId = 0, string k = "")
        {
            return RedirectToAction("CreateUpdate", "Case",new {typeId=typeId,caseId=caseId,k=k});
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseEvent()
        {
            var model = new Dchien.Legal.Web.Areas.IPR.ViewModels.CaseEvent.CaseEventModel();
            return PartialView("CaseEvent", model);
        }

        [HttpPost]
        public JsonResult CaseEventCreate(Dchien.Legal.Web.Areas.IPR.ViewModels.CaseEvent.CaseEventModel model)
        {
            var response = new PostResponse();
            var caseList = CaseService.Instance.GetCaseBasic(model.CaseIds);
            var caseEvents = new List<BizCaseEvent>();

            caseList.ForEach(c =>
            {
                var caseEvent = new BizCaseEvent();
                caseEvent.CaseId = c.CaseBasicInfo.CaseId;
                caseEvent.CaseNo = c.CaseBasicInfo.CaseNo;
                caseEvent.CompanyId = c.CaseBasicInfo.CompanyId;
                caseEvent.EventTypeId = (int)CaseEventType.EventType0;
                caseEvent.Deadline = model.EventTime;
                caseEvent.EventTime = model.EventTime;
                caseEvent.EventContent = model.EventContent;

                 CaseEventService.Instance.CreateCaseEvent(caseEvent);
             });

            response.Message = "保存成功！";
            response.IsSuccess = true;
            
            return Json(response);
        }


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
