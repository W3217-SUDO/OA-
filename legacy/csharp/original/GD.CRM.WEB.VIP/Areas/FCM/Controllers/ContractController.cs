using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FCM.Contract;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Web.Areas.FCM.ViewModels.Contract;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractController");

        #region  合同列表

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractList(long id,int? contractStatus)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == PageId.PageId_4001002
                || id.ToString() == PageId.PageId_4001006
                || id.ToString() == PageId.PageId_4001007
               ) && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var model = new ListModel();

                model.SearchCondition = new ContractSearchCondition();
                model.SearchCondition.PageNo = 1;
                model.SearchCondition.PageSize = 15;
                model.SearchCondition.PageId = id.ToString();

                if (id.ToString() == PageId.PageId_4001002)
                {
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                    model.SearchCondition.BusinessOwnerName = LoginHelper.GetUserChName();
                }

                if (contractStatus.HasValue)
                {
                    model.SearchCondition.ContractStatus = (ContractStatus)contractStatus.Value;
                }

                return View(model);
            }
            return new RedirectResult("~/NoPermission.html?" + id.ToString());

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.PendingList","ContractController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
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

                if (model.SearchCondition.PageId == PageId.PageId_4001002)
                {
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001006)
                {
                    model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_4001007)
                {
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                }

                var result = new BizContractSearchResultInfo();

                if (model.SearchCondition.PageId == PageId.PageId_5001002001)
                {
                    result.ContractList = ContractService.Instance.GetARContractList(model.SearchCondition);
                    result.ContractList = result.ContractList.FindAll(x => x.ContractBasicInfo.TotalAmount > x.ContractBasicInfo.CashedAmount);
                }
                else
                {
                    result.ContractList = ContractService.Instance.GetContractList(model.SearchCondition);

                }


                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.PendingList","ContractController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ContractStatus = ContractStatus.P;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.PendingList","ContractController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ApprovedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ContractStatus = ContractStatus.A;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractController.ApprovedList","ContractController.ApprovedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult RejectedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ContractStatus = ContractStatus.R;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractController.RejectedList", "ContractController.RejectedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetContractListByCustomerId(long customerId)
        {
            var response = new PostResponse();

            try
            {
                var contractList = ContractService.Instance.GetBasicContractListByCustomerId(customerId);
                response.IsSuccess = true;
                response.Data = contractList;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractController.GetContractListByCustomerId", "ContractController.GetContractListByCustomerId", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        public JsonResult GetContractListByCustomerNo(string customerNo)
        {
            var response = new PostResponse();

            try
            {
                var contractList = ContractService.Instance.GetBasicContractListByCustomerNo(customerNo);
                response.IsSuccess = true;
                response.Data = contractList;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractController.GetContractListByCustomerNo", "ContractController.GetContractListByCustomerNo", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        #endregion

        #region 合同审批

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ToAudit(long  contractId, string auditor)
        {
            var response = new PostResponse();

            var contract = ContractService.Instance.GetContractById(contractId);

            contract.ContractBasicInfo.Auditor = auditor;
            contract.ContractBasicInfo.ContractStatus = ContractStatus.P;

            bool result = ContractService.Instance.ToAudit(contract);

            if (result)
            {
                response.Message = "提交成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "提交失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult ContractObjectList(long contractId)
        {
            var model = new ContractObjectListModel();

            //var contractObjects = ContractService.Instance.GetContractObjects(contractId);

            //model.ContractObjects = contractObjects.Any() ? contractObjects.OrderBy(x => x.CaseId).ToList() : contractObjects;

            //var invoiceObjects = InvoiceService.Instance.GetInvoiceList(contractId);
            //model.InvoicedObjects = invoiceObjects.Any() ? invoiceObjects.OrderBy(x => x.InvoiceBasic.InvoiceId).ToList() : invoiceObjects;

            if (Dchien.Legal.Service.CompanyService.Instance.GetCompany().CompanyCode == "31253")
            {
                var jreceivedObjects = Dchien.Legal.Service.FAM.AR.Payment.PaymentService.Instance.GetPaymentList(contractId);
                model.JReceivedObjects = jreceivedObjects.Any() ? jreceivedObjects.OrderBy(x => x.PaymentBasic.PaymentId).ToList() : jreceivedObjects;
            }
            else
            {
                var receivedObjects = Dchien.Legal.Service.FAM.AR.ReceivedPayment.PaymentService.Instance.GetPaymentList(contractId);
                model.ReceivedObjects = receivedObjects.Any() ? receivedObjects.OrderBy(x => x.PaymentBasic.PaymentId).ToList() : receivedObjects;
            }

            var paidObjects = Dchien.Legal.Service.FAM.AP.Payment.PaymentService.Instance.GetPaymentList(contractId);
            model.PaidObjects = paidObjects.Any() ? paidObjects.OrderBy(x => x.PaymentBasic.PaymentId).ToList() : paidObjects;
            return PartialView("ContractObjectList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public ActionResult ContractObjects(long contractId,int? pageNo, int? pageSize)
        {
            var model = new ContractObjectListModel();

            var contractObjects = ContractService.Instance.GetContractObjects(contractId);

            model.PageSize = pageSize.HasValue ? pageSize.Value : 10;
            model.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            model.TotalCount = contractObjects.Count;

            model.ContractObjects = contractObjects.OrderByDescending(x=>x.CaseId).ThenByDescending(x=>x.CaseOfficeFeeId).Skip(model.PageSize * (model.PageNo - 1))
                            .Take(model.PageSize)
                            .ToList();

            return PartialView("ContractObjects", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        //[HttpPost]
        //[CheckUserLogin]
        //public JsonResult ContractObjects(long? contractId)
        //{
        //    var response = new PostResponse();
        //    response.IsSuccess = true;
        //    var contractObjects = new List<BizContractObject>();

        //    if (contractId.HasValue && contractId > 0)
        //    {
        //        contractObjects = ContractService.Instance.GetContractObjects(contractId.Value);
        //    }

        //    response.Data = contractObjects.Any() ? contractObjects.OrderBy(x => x.CaseId).ToList() : contractObjects;

        //    return Json(response);
        //}

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ContractObjectLogs(long contractId, string batchNo)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            var contractObjects = new List<BizContractObject>();

            contractObjects = ContractService.Instance.GetContractObjectLogs(contractId, batchNo);
 
            response.Data = contractObjects.OrderByDescending(x=>x.LogId).ThenByDescending(x=>x.OperateTime);

            return Json(response);
        }

        #region 合同信息

        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractView(long contractId)
        {
            ViewBag.ContractId = contractId;
            
            return View();
        }

        [CheckUserLogin]
        public ActionResult PreView(string contractNo)
        {
            ViewBag.ContractNo = contractNo;

            return View("ContractView");
        }

        #endregion



        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractIds"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public JsonResult ContractDelete(List<long> contractIds)
        {
            var response = new PostResponse();
            response.IsSuccess = ContractService.Instance.ContractDelete(contractIds);

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractSelectedList(string id)
        {
            var model = new ListModel();

            model.SearchCondition = new ContractSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id.ToString();

            //model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            //model.SearchCondition.BusinessOwnerName = LoginHelper.GetUserChName();
           
            return  PartialView("ContractSelectedList",model);
        }

    }
}
