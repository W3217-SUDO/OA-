using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FCM.ViewModels.Contract;
 
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.ServiceStack.Common;


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractArchiveController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractArchiveController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001008)]
        public ActionResult List(long id)
        {
            var model = new ListModel();
            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult List(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizContractSearchResultInfo();

                result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractArchiveController.List", "ContractArchiveController.List", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult Archive(long contractId)
        {
            var model = new DraftModel();
            model.Contract = ContractService.Instance.GetContractById(contractId);

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Archived(Array caseFeeIds)
        {
            var caseFeeIdList = new Dictionary<long, bool>();

            foreach (var item in caseFeeIds)
            { 
                var caseFeeId = item.ToString().Split(',');

                caseFeeIdList.Add(long.Parse(caseFeeId[0]), bool.Parse(caseFeeId[1]));
            }
            var response = new PostResponse();

            bool result = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.CaseFeeArchived(caseFeeIdList);

            if (result)
            {
                response.Message = "完结成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "完结失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractObjectList(long? contractId)
        {
            var model = new ContractObjectListModel();

            var contractObjects = contractId.HasValue ? ContractService.Instance.GetContractObjects(contractId.Value) : new List<BizContractObject>();

            model.ContractObjects = contractObjects.Any() ? contractObjects.OrderBy(x => x.CaseId).ToList() : contractObjects;

            return PartialView("ContractObjectList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ContractObjects(long? contractId)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            var contractObjects = new List<BizContractObject>();

            if (contractId.HasValue && contractId > 0)
            {
                contractObjects = ContractService.Instance.GetContractObjects(contractId.Value);
            }
            contractObjects.Add(new BizContractObject());
            response.Data = contractObjects;

            return Json(response);
        }


    }
}
