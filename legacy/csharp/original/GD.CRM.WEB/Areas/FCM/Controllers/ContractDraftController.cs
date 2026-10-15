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


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractDraftController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractDraftController");

        [CheckUserLogin]
        public ActionResult DraftList()
        {
            var model = new ListModel();

            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
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
                    model.SearchCondition.PageSize = 15;

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
        public ActionResult Draft(string id,long? customerId, long? contractId)
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

        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_4001001)]
        public ActionResult Create(string id, long? customerId, long? contractId)
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
                        model.Contract.ContractBasicInfo.CustomerId = customer.CustomerBasic.CustomerId;
                        model.Contract.ContractBasicInfo.CustomerName = customer.CustomerBasic.CustomerName;
                        model.Contract.ContractBasicInfo.ContractName = customer.CustomerBasic.CustomerName + "_合同";
                        model.Contract.ContractBasicInfo.CustomerNo = customer.CustomerBasic.CustomerNo;
                    }
                }
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ToAudit(long contractId)
        {
            var contract = ContractService.Instance.GetContractById(contractId);
            var model = new DraftModel();
            model.Contract = contract;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ToOfficialDocumentAudit(long contractId)
        {
            var contract = ContractService.Instance.GetContractById(contractId);
            var model = new DraftModel();
            model.Contract = contract;
            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractObjectList(string id)
        {
            var model = new ContractObjectListModel();
            model.PageNo = 1;
            model.PageSize = 10;
            return PartialView("ContractObjectList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ContractObjects(long? contractId, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            var contractObjects = new List<BizContractObject>();

            if (contractId.HasValue && contractId > 0)
            {
                contractObjects = ContractService.Instance.GetContractObjects(contractId.Value);
            }

            if (!pageNo.HasValue) pageNo = 1;
            if (!pageSize.HasValue) pageSize = 10;

            var resultInfo = new BizContractObjectSearchResultInfo();

            resultInfo.PageSize = pageSize.Value;
            resultInfo.PageNo = pageNo.Value;
            resultInfo.TotalItemCount = contractObjects.Count + 1;

            contractObjects = contractObjects.Skip(pageSize.Value * (pageNo.Value - 1))
                            .Take(pageSize.Value)
                            .OrderByDescending(x => x.CaseOfficeFeeId)
                            .ToList();

            contractObjects.Add(new BizContractObject());

            resultInfo.ContractObjectList = contractObjects;

            response.Data = resultInfo;

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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractObjects"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ContractObjectsCreate(List<BizContractObject> contractObjects)
        {
            var response = new PostResponse();

            try
            {
                if (contractObjects != null && contractObjects.Any())
                {
                    contractObjects.ForEach(x =>
                    { 
                        var contract = ContractService.Instance.GetContractByNo(x.ContractNo);
                        x.ContractNo = contract.ContractBasicInfo.ContractNo;
                        x.ContractId = contract.ContractBasicInfo.ContractId;
                        x.CustomerId = contract.ContractBasicInfo.CustomerId;
                    });
                }
                var caseFeeList = ContractService.Instance.CreateContractObjects(contractObjects);
                if (caseFeeList != null && caseFeeList.Any())
                {
                    response.Message = "保存成功！";
                    response.Data = new { CaseFeeIds = caseFeeList.Select(x=>x.CaseFeeId) };
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
                response.IsSuccess = false;
            }
            return Json(response);
        }

    }
}
