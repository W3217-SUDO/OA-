using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FAM.Invoice;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.Invoice;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.BAS.Type;
using Dchien.Legal.Web.Areas.FAM.ViewModels.Invoice;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InvoiceController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InvoiceController");

        #region 发票申请


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceCreate(long contractId, string caseFeeIds)
        {
            var model = new InvoiceCreateModel();
            model.Invoice = InvoiceService.Instance.CreateInvoice(contractId);

            if (model.Invoice != null)
            {
                var contract = ContractService.Instance.GetContractBasicById(contractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
                model.Invoice.InvoiceBasic.InvoiceName = model.Customer.CustomerBasic.CustomerName;

                model.Invoice.InvoiceBasic.CustomerCompanyCode = model.Customer.CustomerRegistration.LicenseNo;
                model.Invoice.InvoiceBasic.CustomerBankAccount = model.Customer.CustomerRegistration.BankAccount;
                model.Invoice.InvoiceBasic.CustomerBankName = model.Customer.CustomerRegistration.AccountBankName;
                model.Invoice.InvoiceBasic.CustomerBusinessAddress = !string.IsNullOrEmpty(model.Customer.CustomerBasic.ContactAddress) ? model.Customer.CustomerBasic.ContactAddress : model.Customer.CustomerRegistration.RegistrationAddress;
                model.Invoice.InvoiceBasic.CustomerPhone = model.Customer.CustomerBasic.ContactPhone;
            }

            //model.Invoice.InvoiceObjects = model.Invoice.InvoiceObjects.FindAll(x => x.CaseOfficeFeeOpenInvoiceAmount > 0 || x.CaseNonOfficeFeeOpenInvoiceAmount > 0 || x.CaseCommissionFeeOpenInvoiceAmount > 0).OrderByDescending(x => x.InformDate).Take(300).ToList();
            model.Invoice.InvoiceObjects = model.Invoice.InvoiceObjects.FindAll(x => x.CaseFeeOpenInvoiceAmount > 0 ).OrderByDescending(x => x.InformDate).Take(300).ToList();

            if (!string.IsNullOrEmpty(caseFeeIds))
            {
                var caseFeeIdList = caseFeeIds.Split(',').ToList();
                model.Invoice.InvoiceObjects = model.Invoice.InvoiceObjects.FindAll(x => caseFeeIds.Contains(x.CaseFeeId.ToString()));
            }

            return View(model);
        }



        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceDetailCreate(string customerNo, string contractNos, string caseFeeIds)
        {
            var model = new InvoiceCreateModel();
            model.Invoice = InvoiceService.Instance.CreateInvoiceDetail();

            if (model.Invoice != null)
            {
                model.Customer =  CustomerService.Instance.GetCustomerByNo(customerNo);
                if (model.Customer == null)
                {
                    throw new ApplicationException(string.Format(string.Format("未找到客户{0}",customerNo)));
                }
                model.Invoice.InvoiceBasic.InvoiceName = model.Customer.CustomerBasic.CustomerName;
                model.Invoice.InvoiceBasic.CustomerCompanyCode = model.Customer.CustomerRegistration.LicenseNo;
                model.Invoice.InvoiceBasic.CustomerBankAccount = model.Customer.CustomerRegistration.BankAccount;
                model.Invoice.InvoiceBasic.CustomerBankName = model.Customer.CustomerRegistration.AccountBankName;
                model.Invoice.InvoiceBasic.CustomerBusinessAddress = !string.IsNullOrEmpty(model.Customer.CustomerBasic.ContactAddress) ? model.Customer.CustomerBasic.ContactAddress : model.Customer.CustomerRegistration.RegistrationAddress;
                model.Invoice.InvoiceBasic.CustomerPhone = model.Customer.CustomerBasic.ContactPhone;

                model.SearchCondition = new Entity.FAM.AR.CaseFee.CaseFeeSearchCondition();
                model.SearchCondition.CustomerNo = customerNo;
                model.SearchCondition.ContractNo = contractNos;
                model.SearchCondition.CaseFeeId = caseFeeIds;
                model.SearchCondition.PaymentInvoicedStatus = (int)Dchien.Legal.Entity.FAM.AR.CaseFee.PaymentInvoicedStatus.UnInvoiced;
            }

            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceCreateUpdate(BizInvoice invoice)
        {
            var response = new PostResponse();

            var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

            try
            {
                invoice.InvoiceBasic.InvoiceAmount =
                    invoice.InvoiceServices.Sum(x => x.Amount.HasValue ? x.Amount.Value : 0);

                if (invoice.InvoiceBasic.InvoiceAmount == 0)
                {
                    response.Message = "实际开票金额为零.";
                    response.IsSuccess = false;
                    return Json(response);
                }

                decimal invoceTotalAmount = 0;

                invoice.InvoiceObjects.ForEach(x =>
                {
                    var caseFee = CaseFeeService.Instance.GetCaseFeeByCaseFeeId(x.CaseFeeId.Value);

                    if (caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId) != null
                    && caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId).TypeId == CaseFeeTypeId.Office)
                    {
                        invoice.InvoiceBasic.CaseOfficeFeeAmount += x.CaseFeeInvoiceAmount.HasValue ? x.CaseFeeInvoiceAmount.Value : 0;

                    }
                    else if (caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId) != null
                   && caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId).TypeId == CaseFeeTypeId.NonOffice)
                    {
                        invoice.InvoiceBasic.CaseNonOfficeFeeAmount += x.CaseFeeInvoiceAmount.HasValue ? x.CaseFeeInvoiceAmount.Value : 0;
                    }
                    else if (caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId) != null
                 && caseFeeTypes.FirstOrDefault(f => f.FeeTypeId == caseFee.CaseFeeTypeId).TypeId == CaseFeeTypeId.Commission)
                    {
                        invoice.InvoiceBasic.CaseCommissionFeeAmount += x.CaseFeeInvoiceAmount.HasValue ? x.CaseFeeInvoiceAmount.Value : 0;
                    }

                    invoceTotalAmount += (caseFee.Amount.Value - caseFee.InvoicedAmount.Value);
                });

                invoice.InvoiceBasic.InvoiceOverAmount = invoice.InvoiceBasic.InvoiceAmount - invoceTotalAmount;

                if (invoice.InvoiceBasic.InvoiceOverAmount < 0)
                {
                    response.Message = "实际开票金额不允许小于所选案件开票金额.！";
                    response.IsSuccess = false;
                    return Json(response);
                }

                bool result = InvoiceService.Instance.InvoiceCreateUpdate(invoice);

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

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"InvoiceController.InvoiceCreateUpdate","InvoiceController.InvoiceCreateUpdate", ex);
            }
            return Json(response);
        }

        #endregion

        #region 发票列表
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [PermissionAttribute(Dchien.Legal.Entity.System.PageId.PageId_5001006001)]
        public ActionResult InvoiceList(string id)
        {
            var listModel = new ListModel();
            listModel.SearchCondition = new InvoiceSearchCondition();
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.InvoiceApplicant = LoginHelper.GetUserName();
            listModel.SearchCondition.InvoiceApplicantName = LoginHelper.GetUserChName();
            return View(listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvoiceSearchResultInfo();

                model.SearchCondition.InvoiceApplicant = LoginHelper.GetUserName();

                result.InvoiceList = InvoiceService.Instance.GetInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"InvoiceController.InvoiceList","InvoiceController.InvoiceList", ex);
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
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvoiceSearchResultInfo();

                model.SearchCondition.InvoiceStatus = InvoiceStatus.Pending;

                result.InvoiceList = InvoiceService.Instance.GetInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"InvoiceController.InvoiceList","InvoiceController.InvoiceList", ex);
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
        public JsonResult InvoicedList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvoiceSearchResultInfo();

                result.InvoiceList = InvoiceService.Instance.GetInvoiceList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvoiceController.InvoicedList", "InvoiceController.InvoicedList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion

        #region 发票查看

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvoiceView(long invoiceId)
        {
            var model = new InvoiceCreateModel();

            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            if (invoice != null)
            {
                model.Invoice = invoice;

                model.Customer = CustomerService.Instance.GetCustomerById(model.Invoice.InvoiceBasic.CustomerId);
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <returns></returns>
        public ActionResult InvoiceEdit(long invoiceId)
        {
            var model = new InvoiceCreateModel();

            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            if (invoice != null)
            {
                model.Invoice = invoice;
                var contract = ContractService.Instance.GetContractBasicById(invoice.InvoiceBasic.ContractId);

                model.Contract = contract;
                model.Customer = contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View(model);
        }

        #endregion

        #region 发票号修改

        [HttpPost]
        [CheckUserLogin]
        public ActionResult InvoiceNoChange(long invoiceId)
        {
            var model = new InvoiceModel();

            model.Invoice = InvoiceService.Instance.GetInvoiceBasic(invoiceId);

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <param name="invoiceNo"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceNoUpdate(long invoiceId, string invoiceNo)
        {
            var response = new PostResponse();

            try
            {
               var invoice = InvoiceService.Instance.GetInvoiceBasic(invoiceId);

                invoice.InvoiceBasic.InvoiceNo = invoiceNo;

                var result = InvoiceService.Instance.ChangeInvoiceNo(invoice);

                if (result)
                {
                    response.Message = "修改成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "修改失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"InvoiceController.InvoiceNoUpdate","InvoiceController.InvoiceNoUpdate", ex);
            }
            return Json(response);
        }

        #endregion

        #region 发票号修改

        [HttpPost]
        [CheckUserLogin]
        public ActionResult InvoiceDateChange(long invoiceId)
        {
            var model = new InvoiceModel();

            model.Invoice = InvoiceService.Instance.GetInvoiceBasic(invoiceId);

            return PartialView(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <param name="invoiceNo"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceDateUpdate(long invoiceId, DateTime? invoiceApplicationDate,DateTime? invoiceDate)
        {
            var response = new PostResponse();

            try
            {
                var invoice = InvoiceService.Instance.GetInvoiceBasic(invoiceId);

                invoice.InvoiceBasic.InvoiceApplicationDate = invoiceApplicationDate;
                invoice.InvoiceBasic.InvoiceDate = invoiceDate;

                var result = InvoiceService.Instance.ChangeInvoiceDate(invoice);

                if (result)
                {
                    response.Message = "修改成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "修改失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvoiceController.InvoiceNoUpdate", "InvoiceController.InvoiceNoUpdate", ex);
            }
            return Json(response);
        }

        #endregion

        [CheckUserLogin]
        public ActionResult InvoiceCancel(long invoiceId)
        {
            var model = new InvoiceModel();

            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            if (invoice != null)
            {
                model.Invoice = invoice;
                model.Customer = CustomerService.Instance.GetCustomerById(invoice.InvoiceBasic.CustomerId);
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InvoiceCanceled(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                var orginvoice = InvoiceService.Instance.GetInvoice(invoice.InvoiceBasic.InvoiceId.Value);

                if (orginvoice == null)
                {
                    response.Message = "作废失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                orginvoice.InvoiceBasic.InvoiceCancelCause = invoice.InvoiceBasic.InvoiceCancelCause;
                orginvoice.InvoiceBasic.InvoiceStatus = InvoiceStatus.InvoiceCanceled;

                bool result = InvoiceService.Instance.InvoiceCanceled(orginvoice);

                if (result)
                {
                    response.Message = "作废成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "作废失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"InvoiceController.InvoiceCanceled","InvoiceController.InvoiceCanceled", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoiceId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ApplicationCancel(long invoiceId)
        {
            var model = new InvoiceModel();

            var invoice = InvoiceService.Instance.GetInvoice(invoiceId);

            if (invoice != null)
            {
                model.Invoice = invoice;
                model.Customer = CustomerService.Instance.GetCustomerById(invoice.InvoiceBasic.CustomerId);
            }

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="invoice"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult ApplicationCanceled(BizInvoice invoice)
        {
            var response = new PostResponse();

            try
            {
                var orginvoice = InvoiceService.Instance.GetInvoice(invoice.InvoiceBasic.InvoiceId.Value);

                if (orginvoice == null)
                {
                    response.Message = "撤回失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                orginvoice.InvoiceBasic.ApplicationCancelCause = invoice.InvoiceBasic.ApplicationCancelCause;
                orginvoice.InvoiceBasic.InvoiceStatus = InvoiceStatus.ApplicaionCanceled;

                bool result = InvoiceService.Instance.ApplicationCanceled(orginvoice);

                if (result)
                {
                    response.Message = "撤回成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "撤回失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvoiceController.ApplicationCanceled", "InvoiceController.ApplicationCanceled", ex);
            }
            return Json(response);
        }

    }
}
