using System;
using System.Collections.Generic;
using System.Diagnostics.Contracts;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FCM.Contract.File;
using Dchien.Legal.Service.FCM.Contract.Event;
using Dchien.Legal.Web.Areas.FCM.ViewModels.ContractEvent;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using BizContractFile = Dchien.Legal.BizModel.FCM.Contract.BizContractFile;


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractEventController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractEventController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractEventList()
        {
            var model = new ContractEventListModel();

            return PartialView("ContractEventList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ViewContractEventList()
        {
            var model = new ContractEventListModel();

            return PartialView("View/ContractEventList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult ContractEvents(string contractGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var events = new List<BizContractEvent>();

            if (!string.IsNullOrEmpty(contractGuid))
            {
                events = ContractEventService.Instance.GetContractEventList(contractGuid);
            }

            response.Data = events;

            return Json(response);
        }

        [CheckUserLogin]
        public ActionResult ContractEvent()
        {
            var model = new ContractEventModel();

            return PartialView("ContractEvent", model);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <param name="content"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult ContractEventCreate(string contractGuid,string content)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var contractEvent = new BizContractEvent();

            contractEvent.ContractGuid = contractGuid;
            contractEvent.Content = content;
            contractEvent.OperateTime = DateTime.Now;

            ContractEventService.Instance.Create(contractEvent);

            return Json(response);
        }
    }
}
