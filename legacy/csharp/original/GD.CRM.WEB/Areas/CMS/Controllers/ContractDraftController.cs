using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Areas.FCM.ViewModels.Contract;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CMS.Controllers
{
    [CheckUserLogin]
    public class ContractDraftController : Controller
    {
        internal Log Logger = new Log("CMS.Controllers.ContractDraftController");

        [CheckUserLogin]
        public ActionResult DraftList()
        {
            var model = new ListModel();

            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.ContractStatus = ContractStatus.D;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult DraftList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 20;

                model.SearchCondition.ContractStatus = ContractStatus.D;
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractController.DraftList", "ContractController.DraftList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001001)]
        public ActionResult Draft(long? customerId, long? contractId)
        {
            var model = new DraftModel();

            if (contractId.HasValue)
            {
                model.Contract = ContractService.Instance.GetContractById(contractId.Value);
            }
            else
            {
                model.Contract = new BizContract();
                model.Contract.ContractBasicInfo = new BizContractBasic();
                model.Contract.ContractBasicInfo.ContractGuid = Guid.NewGuid().ToString();
                model.Contract.ContractBasicInfo.AuditDate = DateTime.Now;
                model.Contract.ContractBasicInfo.BusinessOwner = LoginHelper.GetUserName();
                model.Contract.ContractBasicInfo.BusinessOwnerName = LoginHelper.GetUserChName();
                model.Contract.ContractBasicInfo.TotalAmount = 0;
                model.Contract.ContractBasicInfo.CaseOfficeFeeAmount = 0;
                model.Contract.ContractBasicInfo.CaseNonOfficeFeeAmount = 0;
                model.Contract.ContractBasicInfo.CaseCommissionAmount = 0;
                model.Contract.ContractBasicInfo.CashedAmount = 0;
                model.Contract.ContractBasicInfo.CashedTimes = 0;
                model.Contract.ContractBasicInfo.ARAmount = 0;
                model.Contract.ContractBasicInfo.APAmount = 0;
                model.Contract.ContractBasicInfo.PaidTimes = 0;
                model.Contract.ContractBasicInfo.PaidCaseFeeAmount = 0;
                model.Contract.ContractBasicInfo.UnPaidCaesFeeAmount = 0;
                model.Contract.ContractBasicInfo.InvoicedAmount = 0;
                model.Contract.ContractBasicInfo.InvoiceAmount = 0;
                model.Contract.ContractBasicInfo.InvoicedTimes = 0;

                if (customerId.HasValue)
                {
                    var customer = CustomerService.Instance.GetCustomerById(customerId.Value);
                    if (customer != null)
                    {
                        model.Contract.ContractBasicInfo.CustomerId =  customer.CustomerBasic.CustomerId;
                        model.Contract.ContractBasicInfo.CustomerName =  customer.CustomerBasic.CustomerName;
                        model.Contract.ContractBasicInfo.ContractName =  customer.CustomerBasic.CustomerName + "_合同";
                        model.Contract.ContractBasicInfo.CustomerNo =  customer.CustomerBasic.CustomerNo;
                    }
                }
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractObjectList(long? id)
        {
            var model = new ContractObjectListModel();

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


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contract"></param>
        /// <param name="contractObjects"></param>
        /// <returns></returns>
         public JsonResult DraftCreate(BizContract contract, List<BizContractObject> contractObjects)
        {
            var response = new PostResponse();

            try
            {
                bool result = ContractService.Instance.DarftCreateUpdate(contract, contractObjects);

                if (result)
                {
                    var model = new DraftModel();
                    model.Contract = contract;
                    model.ContractObjects = contractObjects;
                    response.Data = model;
                    response.Message = "保存成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "保存失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = true;
            }
            return Json(response);
        }

    }
}
