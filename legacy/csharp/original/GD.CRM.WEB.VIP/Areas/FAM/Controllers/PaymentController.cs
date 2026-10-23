using System;
using System.Web.Mvc;
using System.Collections.Generic;
using System.Linq;

using Dchien.Legal.BizModel.FAM.AP.Payment.Audit;
using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.FAM.AP.Payment;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class PaymentController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.PaymentController");

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

                if (CommonService.Instance.PaymentAutoAudit())
                {
                    var audit = new BizPaymentAudit();

                    audit.PaymentId = payment.PaymentBasic.PaymentId.Value;
                    audit.AuditFlowId = payment.PaymentBasic.AuditFlowId;
                    audit.AuditFlowNodeId = payment.PaymentBasic.AuditFlowNodeId;
                    audit.AuditRoundId = payment.PaymentBasic.AuditRoundId;
                    audit.Auditor = "System";
                    audit.AuditStatus = AuditStatus.A;

                    PaymentService.Instance.Audit(audit);
                }
     

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentCreateUpdate", "PaymentController.PaymentCreateUpdate", ex);
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
        public JsonResult PaymentObjectsCreateUpdate(List<BizPaymentObject> paymentObjects)
        {
            var response = new PostResponse();

            try
            {
                var lst = paymentObjects.GroupBy(x => new { x.PaymentTypeId, x.ContractNo }).ToList();

                var paymentList = new List<BizPayment>();

                lst.ForEach(x =>
                {
                    var payment = new BizPayment();
                    payment.PaymentBasic = new BizPaymentBasic();
                    payment.PaymentType = new BizPaymentType();
                    payment.PaymentObjects = new List<BizPaymentObject>();

                    var contract = ContractService.Instance.GetContractBasicByNo(x.Key.ContractNo);
                    var customer = CustomerService.Instance.GetCustomerBasicByNo(contract.ContractBasicInfo.CustomerNo);
                   
                    payment.PaymentBasic.CustomerId = contract.ContractBasicInfo.CustomerId.Value;
                    payment.PaymentBasic.CustomerNo = contract.ContractBasicInfo.CustomerNo;
                    payment.PaymentBasic.ContractId = contract.ContractBasicInfo.ContractId.Value;
                    payment.PaymentBasic.ContractNo = contract.ContractBasicInfo.ContractNo;
                    payment.PaymentBasic.ApplicationNo = "P" + DateTime.Now.ToString("yyMMddHHmmssfff");
                    payment.PaymentBasic.ApplicationDate = DateTime.Now;
                    payment.PaymentBasic.PayerName = customer.CustomerBasic.CustomerName;
                    payment.PaymentType.PaymentTypeId  = x.Key.PaymentTypeId;
                    payment.PaymentObjects = paymentObjects.FindAll(p => p.ContractNo == x.Key.ContractNo && p.PaymentTypeId == x.Key.PaymentTypeId);

                    payment.PaymentBasic.PaidAmount = payment.PaymentObjects.Sum(f=> f.CaseFeePaidAmount.HasValue ? f.CaseFeePaidAmount.Value : 0);

                    bool result = PaymentService.Instance.PaymentCreateUpdate(payment);

                    payment.PaymentType = PaymentTypeService.Instance.GetPaymentTypeById(x.Key.PaymentTypeId);

                    paymentList.Add(payment);

                    if (CommonService.Instance.PaymentAutoAudit())
                    {
                        var audit = new BizPaymentAudit();

                        audit.PaymentId = payment.PaymentBasic.PaymentId.Value;
                        audit.AuditFlowId = payment.PaymentBasic.AuditFlowId;
                        audit.AuditFlowNodeId = payment.PaymentBasic.AuditFlowNodeId;
                        audit.AuditRoundId = payment.PaymentBasic.AuditRoundId;
                        audit.Auditor = "System";
                        audit.AuditStatus = AuditStatus.A;

                        PaymentService.Instance.Audit(audit);
                    }
                });

                if (paymentList != null && paymentList.Any())
                {
                    response.Message = "提交成功！";
                    response.Data = new { PaymentList = paymentList };
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentObjectsCreateUpdate", "PaymentController.PaymentObjectsCreateUpdate", ex);
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
        public JsonResult PaymentList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                if (PageId.PageId_5001003006 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentStatus = (int)PaymentStatus.Packing;
                }
                else if (PageId.PageId_5001003004 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentStatusList = new List<int>();
                    model.SearchCondition.PaymentStatusList.Add((int)PaymentStatus.Packing);
                    //model.SearchCondition.PaymentStatusList.Add((int)PaymentStatus.Approved);
                    model.SearchCondition.PaymentStatusList.Add((int)PaymentStatus.Paid);
                }
                else if (PageId.PageId_5001003003 == model.SearchCondition.PageId)
                {
                    model.SearchCondition.PaymentStatus = (int)PaymentStatus.Approved;
                }

                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.TotalPaidAmount = model.SearchCondition.TotalPaidAmount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PaymentController.PaymentList","PaymentController.PaymentList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PaymentController.PaymentCanceled","PaymentController.PaymentCanceled", ex);
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
    }
}
