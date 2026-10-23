using System;
using System.Collections.Generic;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM.AR.ReceivedPayment;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AR.ReceivedPayment;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.FAM.AR.ReceivedPayment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class ReceivedPaymentController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.ReceivedPaymentController");
        
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentCreateUpdate", "ReceivedPaymentController.PaymentCreateUpdate", ex);
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
        public JsonResult PaymentList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();
                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalAppliedAmount = model.SearchCondition.TotalAppliedAmount;
                result.TotalUnAppliedAmount = result.TotalAmount - result.TotalAppliedAmount;
                result.TotalCaseOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseOfficeFeeAppliedAmount;
                result.TotalCaseNonOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseNonOfficeFeeAppliedAmount;
                result.TotalCaseCommissionFeeAppliedAmount = model.SearchCondition.TotalCaseCommissionFeeAppliedAmount;
                //结算金额
                result.TotalCaseFeeSettlementAmount = model.SearchCondition.TotalCaseFeeSettlementAmount;
                result.TotalCaseNonOfficeFeeSettlementAmount = model.SearchCondition.TotalCaseNonOfficeFeeSettlementAmount;
                result.TotalCaseFeeArchiveAmount = model.SearchCondition.TotalCaseFeeArchiveAmount;

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
        public JsonResult PaymentPublicList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                model.SearchCondition.IsPublic = true;

                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalAppliedAmount = model.SearchCondition.TotalAppliedAmount;
                result.TotalUnAppliedAmount = result.TotalAmount - result.TotalAppliedAmount;

                result.TotalCaseOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseOfficeFeeAppliedAmount;
                result.TotalCaseNonOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseNonOfficeFeeAppliedAmount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentPublicList", "PaymentController.PaymentPublicList", ex);
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
        public JsonResult PaymentApplyList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalAppliedAmount = model.SearchCondition.TotalAppliedAmount;
                result.TotalUnAppliedAmount = result.TotalAmount - result.TotalAppliedAmount;

                result.TotalCaseOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseOfficeFeeAppliedAmount;
                result.TotalCaseNonOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseNonOfficeFeeAppliedAmount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentApplyList", "PaymentController.PaymentApplyList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentAppliedList(Dchien.Legal.Web.Areas.FAM.ViewModels.AR.ReceivedPayment.ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                model.SearchCondition.ToBeAssigned = false;

                var result = new BizPaymentSearchResultInfo();

                result.PaymentList = PaymentService.Instance.GetPaymentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.TotalAmount = model.SearchCondition.TotalAmount;
                result.TotalAppliedAmount = model.SearchCondition.TotalAppliedAmount;
                result.TotalUnAppliedAmount = result.TotalAmount - result.TotalAppliedAmount;

                result.TotalCaseOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseOfficeFeeAppliedAmount;
                result.TotalCaseNonOfficeFeeAppliedAmount = model.SearchCondition.TotalCaseNonOfficeFeeAppliedAmount;

                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PaymentAppliedList", "PaymentController.PaymentAppliedList", ex);
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
        public JsonResult PaymentPush(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {

                bool result = PaymentService.Instance.PaymentPush(payment);

                if (result)
                {
                    response.Message = "回款领取成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "回款领取失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentPush", "ReceivedPaymentController.PaymentPush", ex);
            }
            return Json(response);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentApply(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {
                bool result = PaymentService.Instance.PaymentApply(payment);

                if (result)
                {
                    payment = PaymentService.Instance.GetPaymentById(payment.PaymentBasic.PaymentId.Value);
                    response.Data = payment;
                    response.Message = "回款分配成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "回款分配失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentApply", "ReceivedPaymentController.PaymentApply", ex);
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
        public JsonResult PaymentAppliedCancel(BizPayment payment)
        {
            var response = new PostResponse();

            try
            {

                bool result = PaymentService.Instance.PaymentAppliedCancel(payment);

                if (result)
                {
                    payment = PaymentService.Instance.GetPaymentById(payment.PaymentBasic.PaymentId.Value);
                    response.Data = payment;
                    response.Message = "回款分配成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "回款分配失败！";
                    response.IsSuccess = false;
                }
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentApply", "ReceivedPaymentController.PaymentApply", ex);
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentDelete(List<long> paymentIds)
        {
            var response = new PostResponse();
            try
            {
                paymentIds.ForEach(paymentId =>
                {
                    PaymentService.Instance.Delete(paymentId);
                });
       
                response.IsSuccess = true;
                response.Data = paymentIds[0];
            }
            catch (ApplicationException ex)
            {
                response.IsSuccess = false;
                response.Message = ex.Message;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ARController.PaymentDelete", "ARController.PaymentDelete", ex);
                response.IsSuccess = false;
                response.Message = "删除出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="paymentId"></param>
        /// <returns></returns>

        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentObjectAppliedList(long paymentId,string pageId)
        {
            var response = new PostResponse();

            try
            {
                var searchCondition = new PaymentObjectSearchCondition();
             
                searchCondition.PageNo = 1;
                searchCondition.PageSize = 1000;

                searchCondition.PaymentId = paymentId;
                searchCondition.PageId = pageId;
                var PaymentObjects = PaymentService.Instance.GetPaymentObjectList(searchCondition);
                response.IsSuccess = true;
                response.Data = PaymentObjects;

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentObjectAppliedList", "ReceivedPaymentController.PaymentObjectAppliedList", ex);
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
        public JsonResult PaymentObjectList(PaymentObjectListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 100;
                model.SearchCondition.FeeTypeId = (int)CaseFeeTypeId.NonOffice;
                if (model.SearchCondition.PageId == PageId.PageId_5001008001 
                    || model.SearchCondition.PageId == PageId.PageId_5001008002
                    || model.SearchCondition.PageId == PageId.PageId_5001008003
                    || model.SearchCondition.PageId == PageId.PageId_5001008004)
                {
                    model.SearchCondition.GroupId = (int)GroupId.Lawfirm;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_50001008001
                    || model.SearchCondition.PageId == PageId.PageId_50001008002
                    || model.SearchCondition.PageId == PageId.PageId_50001008003
                    || model.SearchCondition.PageId == PageId.PageId_50001008004)
                {
                    model.SearchCondition.GroupId = (int)GroupId.Trad;
                }
                if (model.SearchCondition.PageId == PageId.PageId_5001008001 || model.SearchCondition.PageId == PageId.PageId_50001008001)
                {
                    var phaseIds = new List<int>();
                    phaseIds.Add((int)CasePhaseType.Phase_106012);
                    phaseIds.Add((int)CasePhaseType.Phase_206012);
                    phaseIds.Add((int)CasePhaseType.Phase_306012);
                    phaseIds.Add((int)CasePhaseType.Phase_406012);
                    phaseIds.Add((int)CasePhaseType.Phase_506012);
                    phaseIds.Add((int)CasePhaseType.Phase_106018);
                    
                    model.SearchCondition.CasePhaseIdNotIn = phaseIds;

                    model.SearchCondition.SettlementStatusList = new List<int>();
                    model.SearchCondition.SettlementStatusList.Add((int)SettlementStatus.A);
                    model.SearchCondition.SettlementStatusList.Add((int)SettlementStatus.Paid);
                    //model.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.UnSettlemented;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_5001008002 || model.SearchCondition.PageId == PageId.PageId_50001008002)
                {
                    var phaseIds = new List<int>();
                    phaseIds.Add((int)CasePhaseType.Phase_106012);
                    phaseIds.Add((int)CasePhaseType.Phase_206012);
                    phaseIds.Add((int)CasePhaseType.Phase_306012);
                    phaseIds.Add((int)CasePhaseType.Phase_406012);
                    phaseIds.Add((int)CasePhaseType.Phase_506012);
                    phaseIds.Add((int)CasePhaseType.Phase_106018);
                    model.SearchCondition.CasePhaseId = string.Join(",", phaseIds);
                    model.SearchCondition.SettlementStatus = (int)SettlementStatus.Paid;
                    model.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.P;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_5001008003 || model.SearchCondition.PageId == PageId.PageId_50001008003)
                {
                    model.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.Settlemented;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_5001008004 || model.SearchCondition.PageId == PageId.PageId_50001008004)
                {
                    model.SearchCondition.ArchiveAmountSettlementStatus = (int)ArchiveAmountSettlementStatus.Rejected;
                }
                else
                {
                    throw new ArgumentException("无效的PageId.");
                }
                var PaymentObjects = PaymentService.Instance.GetPaymentObjectList(model.SearchCondition);
                var result = new BizPaymentObjectSearchResultInfo();
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                result.TotalArchiveAmount = model.SearchCondition.TotalArchiveAmount;
                result.TotalAppliedAmount = model.SearchCondition.TotalAppliedAmount;
                result.PaymentObjectList = PaymentObjects;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReceivedPaymentController.PaymentObjectList", "ReceivedPaymentController.PaymentObjectList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }
    }
}
