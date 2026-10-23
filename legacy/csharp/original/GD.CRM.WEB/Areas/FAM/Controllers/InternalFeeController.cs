using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Web.UI.WebControls;
using System;
using System.Text;
using System.Web;
using System.Web.UI;
using System.IO;

using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.BizModel.FAM.InternalFee;
using Dchien.Legal.BizModel.FAM.InternalFee.Payment;
using Dchien.Legal.BizModel.FAM.InternalFee.Payment.Packing;
using Dchien.Legal.Entity.FAM.InternalFee.Payment;
using Dchien.Legal.Entity.FAM.InternalFee.Payment.Packing;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FAM.InternalFee;
using Dchien.Legal.Service.FAM.InternalFee.Payment;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.Packing;
using Dchien.Legal.Entity.FAM.InternalFee;

using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class InternalFeeController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.InternalFeeController");

        #region 内部费用申请付款

        [CheckUserLogin]
        public ActionResult PaymentCreate(string caseNo, string caseFeeIds)
        {
            var model = new PaymentModel();
            model.Case = CaseService.Instance.GetCaseBasic(caseNo);
            model.Customer = CustomerService.Instance.GetCustomerBasicByNo(model.Case.Basic.CustomerNo);
            model.Contract = ContractService.Instance.GetContractByNo(model.Case.Basic.ContractNo);

            model.Payment = PaymentService.Instance.CreatePayment(model.Case.Basic.CaseId, new List<long>());

            if (model.Payment != null)
            { 
                if (!string.IsNullOrEmpty(caseFeeIds))
                {
                    var caseFeeIdList = caseFeeIds.Split(',').ToList();
                    model.Payment.PaymentObjects = model.Payment.PaymentObjects.FindAll(x => caseFeeIdList.Contains(x.InternalFeeId.Value.ToString()));
                }
            }

            return View("Payment/Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        //public ActionResult PaymentMultiCreate(string caseFeeIds)
        //{
        //    var model = new PaymentModel();
        //    model.Case = CaseService.Instance.GetCaseBasic(caseNo);
        //    model.Customer = CustomerService.Instance.GetCustomerBasicByNo(model.Case.Basic.CustomerNo);
        //    model.Contract = ContractService.Instance.GetContractByNo(model.Case.Basic.ContractNo);

        //    model.Payment = PaymentService.Instance.CreatePayment(model.Case.Basic.CaseId, new List<long>());

        //    if (model.Payment != null)
        //    {
        //        if (!string.IsNullOrEmpty(caseFeeIds))
        //        {
        //            var caseFeeIdList = caseFeeIds.Split(',').ToList();
        //            model.Payment.PaymentObjects = model.Payment.PaymentObjects.FindAll(x => caseFeeIdList.Contains(x.InternalFeeId.Value.ToString()));
        //        }
        //    }

        //    return View("Payment/Create", model);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="payment"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentCreateUpdate(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {
                bool result = PaymentService.Instance.PaymentCreateUpdate(payment);

                if (result)
                {
                    response.Message = "提交成功！";
                    response.Data = new { PaymentId = payment.PaymentBasic.PaymentId.Value };
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "提交失败！";
                    response.IsSuccess = false;
                }

            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InternalFeeController.PaymentCreateUpdate", "InternalFeeController.PaymentCreateUpdate", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentView(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {

                model.Case = CaseService.Instance.GetCaseBasic(model.Payment.PaymentBasic.CaseNo);
                model.Contract = ContractService.Instance.GetContractBasicByNo(model.Case.Basic.ContractNo);
                model.Customer = model.Contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(model.Contract.ContractBasicInfo.CustomerId.Value) : null;

            }

            return View("Payment/View", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentEdit(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                model.Case = CaseService.Instance.GetCaseBasic(model.Payment.PaymentBasic.CaseNo);
                model.Contract = ContractService.Instance.GetContractBasicByNo(model.Case.Basic.ContractNo);
                model.Customer = model.Contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(model.Contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("Payment/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentCancel(long paymentId)
        {
            var model = new PaymentModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            if (model.Payment != null)
            {
                model.Case = CaseService.Instance.GetCaseBasic(model.Payment.PaymentBasic.CaseNo);
                model.Contract = ContractService.Instance.GetContractBasicByNo(model.Case.Basic.ContractNo);
                model.Customer = model.Contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(model.Contract.ContractBasicInfo.CustomerId.Value) : null;
            }

            return View("Payment/Cancel", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentList(string id,int? paymentStatus)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004001
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004002
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004003
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004004
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004005
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004006
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004012
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004013)
                && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListModel();
                listModel.SearchCondition = new PaymentSearchCondition();

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004001)
                {
                    //listModel.SearchCondition.Applicant = LoginHelper.GetUserName();
                    //listModel.SearchCondition.ApplicantName = LoginHelper.GetUserChName();
                }

                if (paymentStatus.HasValue)
                {
                    listModel.SearchCondition.PaymentStatus = paymentStatus;
                }

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004012)
                {
                    listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.R;
                }

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004013)
                {
                    listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.ApplicaionCanceled;
                    //listModel.SearchCondition.Applicant = LoginHelper.GetUserName();
                    //listModel.SearchCondition.ApplicantName = LoginHelper.GetUserChName();
                }

                //if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004005)
                //{
                //    listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.Approved;
                //}

                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("Payment/List", listModel);
            }


            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentAuditList(string id)
        {
            var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListModel();
            listModel.SearchCondition = new PaymentSearchCondition();
            listModel.SearchCondition.PageId = id;
            listModel.SearchCondition.PageNo = 1;
            listModel.SearchCondition.PageSize = 15;
            listModel.SearchCondition.PaymentStatus = (int)PaymentStatus.P;
            return View("PaymentAudit/List", listModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentList(Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                if (PageId.PageId_5001004001 == model.SearchCondition.PageId 
                    || PageId.PageId_5001004012 == model.SearchCondition.PageId 
                    || PageId.PageId_5001004013 == model.SearchCondition.PageId)
                {
                    if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.User)
                    {
                        model.SearchCondition.UserId = LoginHelper.GetUserName();
                    }
                }

                if (PageId.PageId_5001004013 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentStatus = (int)PaymentStatus.ApplicaionCanceled;
                }

                    //else if (PageId.PageId_5001004003 == model.SearchCondition.PageId)
                    //{
                    //    model.SearchCondition.PaymentStatus = (int)PaymentStatus.Approved;
                    //}

                    result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentList", "PaymentController.PaymentList", ex);
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
        [CheckUserLogin]
        public JsonResult PendingList(Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;
                var result = new BizPaymentSearchResultInfo();

                if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.All)
                {
                    model.SearchCondition.CompanyId = LoginHelper.GetCompanyId();
                }
                else
                {
                    model.SearchCondition.UserId = LoginHelper.GetUserName();
                }
                
                //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                result.PaymentList = PaymentService.Instance.GetPendingPaymentList(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentList", "PaymentController.PaymentList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentAudit(long paymentId)
        {
            var model = new PaymentAuditModel();

            model.Payment = PaymentService.Instance.GetPayment(paymentId);

            var flowAudits = PaymentAuditService.Instance.GetPaymentAuditList(paymentId);

            model.Audit = flowAudits.FirstOrDefault(f => f.AuditRoundId == model.Payment.PaymentBasic.AuditRoundId
                                                    && f.AuditFlowNodeId == model.Payment.PaymentBasic.AuditFlowNodeId
                                                    && f.AuditFlowId == model.Payment.PaymentBasic.AuditFlowId);

            if (model.Payment != null)
            {
                model.Case = CaseService.Instance.GetCaseBasic(model.Payment.PaymentBasic.CaseNo);
                model.Contract = ContractService.Instance.GetContractBasicByNo(model.Case.Basic.ContractNo);
                model.Customer = model.Contract.ContractBasicInfo.CustomerId.HasValue ? CustomerService.Instance.GetCustomerById(model.Contract.ContractBasicInfo.CustomerId.Value) : null;
             }

            return View("PaymentAudit/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="approved"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PaymentAuditCreate(List<long> paymentIds , bool approved,string auditContent)
        {
            var response = new PostResponse();
            bool result = PaymentService.Instance.Audit(paymentIds, approved, auditContent);

            if (result)
            {
                response.Message = "审核成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "审核失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingPrintOnNo(string packingNo)
        {
            var printModel = new PrintModel();

            printModel.Packing = PaymentPackingService.Instance.GetPaymentPacking(packingNo);
            printModel.Company = CompanyService.Instance.GetCompany();

            return View("PaymentPacking/PrintOnPackingNo", printModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingPrint(string packingNo)
        {
            var printModel = new PrintModel();

            printModel.Packing = PaymentPackingService.Instance.GetPaymentPacking(packingNo);
            printModel.Company = CompanyService.Instance.GetCompany();

            return View("PaymentPacking/Print", printModel);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult Packing(List<long> paymentObjectIds)
        {
            var response = new PostResponse();

            try
            {
                var packageNo = PaymentPackingService.Instance.Packing(paymentObjectIds);

                if (!string.IsNullOrEmpty(packageNo))
                {
                    response.Message = "打包成功！";
                    response.Data = packageNo;
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "打包失败！";
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.PackingOnNo", "PaymentPackingController.PackingOnNo", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentPackingVerify(string packingNo)
        {
            var packingModel = new PackingModel();

            packingModel.Packing = PaymentPackingService.Instance.GetPaymentPacking(packingNo);
            packingModel.Packing.PaymentPackingBasic.PaidDate = DateTime.Now;

            return PartialView("PaymentPacking/PackingVerify", packingModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packing"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult Validate(BizPaymentPacking packing)
        {
            var response = new PostResponse();

            try
            {
                var paymentPacking = PaymentPackingService.Instance.GetPaymentPacking(packing.PaymentPackingBasic.PackageNo);

                if (paymentPacking == null)
                {
                    response.Message = "核销成功！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                paymentPacking.PaymentPackingBasic.PaidDate = packing.PaymentPackingBasic.PaidDate;
                paymentPacking.PaymentPackingBasic.PaymentMode = packing.PaymentPackingBasic.PaymentMode;
                paymentPacking.PaymentPackingBasic.InvoiceNo = packing.PaymentPackingBasic.InvoiceNo;
                paymentPacking.PaymentPackingBasic.Remark = packing.PaymentPackingBasic.Remark;
                paymentPacking.PaymentPackingBasic.PackingStatus = PaymentPackingStatus.Packing;

                bool result = PaymentPackingService.Instance.Validate(paymentPacking);

                if (result)
                {
                    response.Message = "核销成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "核销失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.Validate", "PaymentPackingController.Validate", ex);
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult ClosePacking(string packingNo)
        {
            var response = new PostResponse();

            try
            {
                var result = PaymentPackingService.Instance.ClosePacking(packingNo);

                if (result)
                {
                    response.Message = "付款成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "付款失败！";
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.ClosePacking", "PaymentPackingController.ClosePacking", ex);
                response.IsSuccess = false;
                response.Message = "付款失败.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="payment"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentCanceled(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {
                var orgpayment = PaymentService.Instance.GetPayment(payment.PaymentBasic.PaymentId.Value);

                if (orgpayment == null)
                {
                    response.Message = "撤销失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                orgpayment.PaymentBasic.CancelCause = payment.PaymentBasic.CancelCause;
                orgpayment.PaymentBasic.PaymentStatus = PaymentStatus.ApplicaionCanceled;

                bool result = PaymentService.Instance.ApplicationCanceled(orgpayment);

                if (result)
                {
                    response.Message = "撤销成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "撤销失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentCanceled", "PaymentController.PaymentCanceled", ex);
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentRollback(long paymentId)
        {
            var response = new PostResponse();

            try
            {
                var orgpayment = PaymentService.Instance.GetPayment(paymentId);

                if (orgpayment == null)
                {
                    response.Message = "回滚失败！";
                    response.IsSuccess = true;
                    return Json(response);
                }

                //orgpayment.PaymentBasic.CancelCause = payment.PaymentBasic.CancelCause;
                orgpayment.PaymentBasic.PaymentStatus = PaymentStatus.P;

                bool result = PaymentService.Instance.PaymentRollback(orgpayment);

                if (result)
                {
                    response.Message = "回滚成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "回滚失败！";
                    response.IsSuccess = false;
                }

                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentCanceled", "PaymentController.PaymentCanceled", ex);
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PaymentObjectList(string id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((  id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004003
                || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004004)
                && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListObjectModel();
                listModel.SearchCondition = new PaymentObjectSearchCondition();
 
                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004003)
                {
                    listModel.SearchCondition.PaymentObjectStatus = (int)PaymentObjectStatus.Approved;
                }

                if (id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004004)
                {
                    listModel.SearchCondition.PaymentObjectStatus = (int)PaymentObjectStatus.Paid;
                }

                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("PaymentObject/List", listModel);
            }


            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentObjectList(Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.ListObjectModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                if (PageId.PageId_5001004004 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentObjectStatus = (int)PaymentObjectStatus.Paid;
                }
                else if (PageId.PageId_5001004003 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentObjectStatus = (int)PaymentObjectStatus.Approved;
                }

                result.PaymentList = PaymentObjectService.Instance.GetPaymentObjectList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentObjectList", "PaymentController.PaymentObjectList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="packingNo"></param>
        /// <returns></returns>
        public ActionResult PaymentPackingPrintToWordOnNo(string packingNo)
        {

            //var fileName = PaymentPackingService.Instance.PackingPrintOnExcel(id);
            var fileName = PaymentPackingService.Instance.PackingPrint(packingNo);

            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("gb2312");
            Response.ContentType = "application/vnd.ms-word";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                         HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));

            return File(bytes, "attachment;filename=" + fileName);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult PackingList(string id)
        {
            var menus = MenuService.Instance.GetMenusByCurrentUser();

            if ((id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004004
              || id.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004006)
              && menus.Any(x => x.MenuCode == id.ToString()))
            {
                var listModel = new Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.Packing.ListModel();
                listModel.SearchCondition = new  PaymentPackingSearchCondition();
                listModel.SearchCondition.PageId = id;
                listModel.SearchCondition.PageNo = 1;
                listModel.SearchCondition.PageSize = 15;
                return View("PaymentPacking/PackingList", listModel);
            }
            return new RedirectResult("~/NoPermission.html?" + id.ToString());
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PackingList(Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.Payment.Packing.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentPackingSearchResultInfo();

                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004004)
                {
                    model.SearchCondition.PackingStatus = PaymentPackingStatus.Packing;
                }
                //else if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001004006)
                //{
                //    model.SearchCondition.PackingStatus = PaymentPackingStatus.Paid;
                //}

                if (LoginHelper.GetAccesslevel() == (int)Dchien.Legal.Entity.Account.AccessLevel.User)
                {
                    model.SearchCondition.PaymentObject = LoginHelper.GetUserName();
                }

                result.PaymentPackingList = PaymentPackingService.Instance.GetPaymentPackingList(model.SearchCondition);
                result.TotalPaidAmount = model.SearchCondition.TotalPaidAmount;
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentPackingController.PackingList", "PaymentPackingController.PackingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion

        #region 内部费用新建

        [CheckUserLogin]
        public ActionResult MultiCreate(string caseNos)
        {
            return PartialView("InternalFee/MultiCreate");
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public ActionResult MultiCreateByCaseFee()
        {
            return PartialView("InternalFee/MultiCreateByCaseFee");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="internalFeeObjects"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult InternalFeeObjectsCreate(List<BizInternalFee> internalFeeObjects)
        {
            var response = new PostResponse();
            try
            {
                bool result = InternalFeeService.Instance.CreateUpdate(internalFeeObjects);
                var paymentList = new List<BizPayment>();
                if (result)
                {
                    var lst = internalFeeObjects.GroupBy(x => x.CaseNo).ToList();
                    lst.ForEach(x =>
                    {
                        var c = CaseService.Instance.GetCaseBasic(x.Key);
                        var customer = CustomerService.Instance.GetCustomerBasicByNo(c.Basic.CustomerNo);
                        var contract = ContractService.Instance.GetContractBasicByNo(c.Basic.ContractNo);
                        var payment = new BizPayment();
                        payment.PaymentBasic = new BizPaymentBasic();
                        payment.PaymentObjects = new List<BizPaymentObject>();
                        payment.PaymentBasic.CaseId = c.Basic.CaseId;
                        payment.PaymentBasic.CaseNo = c.Basic.CaseNo;
                        payment.PaymentBasic.CustomerId = customer.CustomerBasic.CustomerId.Value;
                        payment.PaymentBasic.CustomerNo = customer.CustomerBasic.CustomerNo;
                        payment.PaymentBasic.ContractId = contract.ContractBasicInfo.ContractId.Value;
                        payment.PaymentBasic.ContractNo = contract.ContractBasicInfo.ContractNo;
                        payment.PaymentBasic.ApplicationNo =  "P" + DateTime.Now.ToString("yyMMddHHmmssfffff");
                        payment.PaymentBasic.ApplicationDate = DateTime.Now;
                        internalFeeObjects.FindAll(fee => fee.CaseNo == x.Key).ForEach(fee => {
                            var paymentObject = new BizPaymentObject();
                            paymentObject.InternalFeeTypeId = fee.FeeTypeId;
                            paymentObject.PaymentObject = fee.PaymentObject;
                            paymentObject.PaymentObjectName = fee.PaymentObjectName;
                            paymentObject.InternalFeePayAmount = fee.Amount;
                            paymentObject.InternalFeePaidAmount = fee.Amount;
                            paymentObject.InternalFeePrePaidAmount = fee.Amount;
                            paymentObject.InternalFeeId = fee.InternalFeeId;
                            paymentObject.CaseId = fee.CaseId;
                            paymentObject.CaseNo  = fee.CaseNo;
                            payment.PaymentObjects.Add(paymentObject);
                        });
                        paymentList.Add(payment);
                        PaymentService.Instance.PaymentCreateUpdate(payment);
                    });
                    response.Data = new { PaymentList = paymentList };
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
                response.IsSuccess = false;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult MultiCreatePaymentList()
        {
            return PartialView("Payment/MultiCreatePaymentList");
        }


        #endregion

        #region 内部费用审批

        [HttpPost]
        public ActionResult MultiAudit(string paymentIds)
        {
            var model = new PaymentAuditModel();
            model.Payments = PaymentService.Instance.GetPaymentList(paymentIds.Split(',').Select(long.Parse).ToList());
            model.PaymentIds = paymentIds;
            return PartialView("PaymentAudit/MultiAudit", model);
        }

        #endregion

        #region 内部费用查询

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult InternalFeeList(string id)
        {
            var model = new Dchien.Legal.Web.Areas.FAM.ViewModels.InternalFee.ListModel();
            model.SearchCondition = new InternalFeeSearchCondition();
            model.SearchCondition.PageId = id;

            if (id == PageId.PageId_5001004007)
            {
                model.SearchCondition.PaymentObject = LoginHelper.GetUserChName();
            }
            return View("InternalFee/List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InternalFeeList(Dchien.Legal.Entity.FAM.InternalFee.InternalFeeSearchCondition searchCondition)
        {
            var response = new PostResponse();

            try
            {
                if (searchCondition.PageNo == 0)
                    searchCondition.PageNo = 1;
                if (searchCondition.PageSize == 0)
                    searchCondition.PageSize = 15;

                var result = new BizInternalFeeSearchResultInfo();

                result.InternalFeeList = InternalFeeService.Instance.GetInternalFeeList(searchCondition);

                result.TotalItemCount = searchCondition.TotalCount;
                result.PageNo = searchCondition.PageNo;
                result.PageSize = searchCondition.PageSize;
                result.TotalAmount = searchCondition.TotalAmount;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InternalFeeController.InternalFeeList", "InternalFeeController.InternalFeeList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="internalFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InternalFeeListAllExportToExcel(Dchien.Legal.Entity.FAM.InternalFee.InternalFeeSearchCondition searchCondition)
        {
            var internalFees = InternalFeeService.Instance.GetInternalFeeList(searchCondition);
            var fileName = InternalFeeService.Instance.InternalFeeListSelectedExportToExcel(internalFees);
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="internalFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InternalFeeListSelectedExportToExcel(List<long> internalFeeIds)
        {
            var internalFees = InternalFeeService.Instance.GetInternalFeeListByInternalFeeIds(internalFeeIds);
            var fileName = InternalFeeService.Instance.InternalFeeListSelectedExportToExcel(internalFees);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult InternalFeeListExportToExcelDownload(string fileName)
        {
            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
            Response.ContentType = "application/vnd.ms-excel";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName + ".xls");

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName + ".xls"));

            return File(bytes, "attachment;filename=" + fileName);
        }
    }
}
