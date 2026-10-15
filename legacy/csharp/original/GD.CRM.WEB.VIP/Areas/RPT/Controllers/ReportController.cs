using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.RPT.ViewModels.Report;
using Dchien.Legal.Entity.FAM.AR.Payment;
using Dchien.Legal.Service.FAM.AR.Payment;
using Dchien.Legal.Service;
using Dchien.Legal.BizModel.FAM.AR.Payment;

namespace Dchien.Legal.Web.Areas.RPT.Controllers
{
    [CheckUserLogin]
    public class ReportController : Controller
    {
        internal Log Logger = new Log("RPT.Controllers.ReportController");

        [CheckUserLogin]
        public ActionResult CountJPaymentList(string id)
        {
            var model = new CountJPaymentListModel();

            model.SearchCondition = new PaymentSearchCondition();
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
        [CheckUserLogin]
        public JsonResult PaymentList(CountJPaymentListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizPaymentSearchResultInfo();

                result.PaymentList = PaymentService.Instance.CountForPaymentList(model.SearchCondition);

                result.TotalItemCount = result.PaymentList.Count;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                result.TotalCashedAmount = result.PaymentList.Sum(x => x.PaymentBasic.CashedAmount);
                result.TotalCaseOfficeFeeCashedAmount = result.PaymentList.Sum(x => x.PaymentBasic.CaseOfficeFeeCashedAmount);
                result.TotalCaseNonOfficeFeeCashedAmount = result.PaymentList.Sum(x => x.PaymentBasic.CaseNonOfficeFeeCashedAmount);
                result.TotalCaseCommissionFeeCashedAmount = result.PaymentList.Sum(x => x.PaymentBasic.CaseCommissionFeeCashedAmount);

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ReportController.PaymentList", "ReportController.PaymentList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


    }
}
