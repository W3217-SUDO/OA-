using System;
using System.Web.Mvc;
using System.Collections;
using System.Collections.Generic;
using Dchien.Legal.BizModel.FAM.AP.Payment;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.Audit;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.BAS.Type;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class PaymentAuditController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.PaymentAuditController");




        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PendingList(ListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;
                var result = new BizPaymentSearchResultInfo();
                model.SearchCondition.Auditor = LoginHelper.GetUserName();

                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003001
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003002
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003003
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003004
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003005
                || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_5001003006)
                {
                    model.SearchCondition.GroupId = (int)GroupId.Lawfirm;
                }
                if (model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003001
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003002
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003003
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003004
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003005
                    || model.SearchCondition.PageId.ToString() == Dchien.Legal.Entity.System.PageId.PageId_50001003006
                    )
                {
                    model.SearchCondition.GroupId = (int)GroupId.Trad;
                }

                result.PaymentList = PaymentService.Instance.GetPendingPaymentList(model.SearchCondition);
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PaymentController.PendingList", "PaymentController.PendingList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="approved"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PaymentAuditCreate(AuditModel model, bool approved)
        {
            var response = new PostResponse();

            model.Audit.AuditStatus = approved ? AuditStatus.A : AuditStatus.R;
            model.Audit.Auditor = LoginHelper.GetUserName();

            bool result = PaymentService.Instance.Audit(model.Audit);

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
        /// <param name="model"></param>
        /// <param name="approved"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PaymentMultiAuditCreate(List<long> paymentIds, bool approved, string auditContent)
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
    }
}
