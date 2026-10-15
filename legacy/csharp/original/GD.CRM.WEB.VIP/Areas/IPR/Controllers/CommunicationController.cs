using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.Communication;
using SunHold.Legal.Common;
using SunHold.Legal.Entity;
using SunHold.Legal.Entity.IPR.Communication;
using SunHold.Legal.Web.Areas.IPR.ViewModels;
using SunHold.Legal.Service.IPR.Communication;
using SunHold.Legal.Web.Areas.IPR.ViewModels.Communication;
using SunHold.Legal.Web.Controllers;
using SunHold.Legal.Web.Models;

namespace SunHold.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CommunicationController : Controller
    {
        internal Log Logger = new Log("IPR.Controllers.CommunicationController");

        public ActionResult Index()
        {
            var model = new CommunicationListModel();
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult Communication(long? id)
        {
            var model = new CommunicationModel();

            if (id.HasValue)
            {
                model.Communication = CommunicationService.Instance.GetCommunication(id.Value);
                var search = new CommunicationSearchCondition();
                search.CustomerId = model.Communication.CustomerId;
                search.PageNo = 1;
                search.PageSize = 20;
                model.CommunicationLogs = CommunicationService.Instance.GetCommunications(search);
            }
            else
            {
                model.Communication = new BizCommunication();
                model.CommunicationLogs = new List<BizCommunication>();
            }
            return PartialView(model);
        }

        [HttpPost]
        public ActionResult CommunicationLogList(long customerId)
        {
            var model = new CommunicationModel();
            if (customerId > 0)
            {
                var search = new CommunicationSearchCondition();
                search.CustomerId = customerId;
                search.PageNo = 1;
                search.PageSize = 20;
                model.CommunicationLogs = CommunicationService.Instance.GetCommunications(search);
            }
            else
            {
                model.CommunicationLogs = new List<BizCommunication>();
            }

            return PartialView("CommunicationLogList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult List(CommunicationListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                var result = new BizCommunicationSearchResultInfo();

                result.Communications = CommunicationService.Instance.GetCommunications(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;

                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error("List Error:" + ex.Message + " || " + ex.StackTrace);
                response.IsSuccess = false;
                response.Message = ex.Message + " || " + ex.StackTrace;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CreateUpdate(CommunicationModel model)
        {
            var response = new PostResponse();

            bool result = CommunicationService.Instance.CreateUpdate(model.Communication);

            if (result)
            {
                response.IsSuccess = true;
                response.Message = "保存成功.";
            }
            else
            {
                response.IsSuccess = false;
                response.Message = "保存失败.";
            }

            return Json(response);
        } 
    }
}
