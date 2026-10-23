using System.Web.Mvc;
using System.Linq;
using System.Collections.Generic;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Areas.FAM.ViewModels.AP.Payment.PaymentType;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.FAM.AP.Payment;
using Dchien.Legal.BizModel.FAM.AP.Payment;

namespace Dchien.Legal.Web.Areas.FAM.Controllers
{
    [CheckUserLogin]
    public class PaymentTypeController : Controller
    {
        internal Log Logger = new Log("FAM.Controllers.PaymentTypeController");

        public ActionResult PaymentTypeList()
        {
            var model = new  ListModel();

            model.SearchCondition = new Entity.FAM.AP.Payment.PaymentTypeSearchCondition();
            model.SearchCondition.CaseFeeTypeId = (int)CaseFeeTypeId.Office;
            model.SearchCondition.PageSize = 10;
            model.SearchCondition.PageNo = 1;

            return PartialView("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult PaymentTypes(ListModel model)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            if (model.SearchCondition.PageNo == 0)
                model.SearchCondition.PageNo = 1;
            if (model.SearchCondition.PageSize == 0)
                model.SearchCondition.PageSize = 10;

            var result = new BizPaymentTypeSearchResultInfo();

            result.PaymentTypeList = PaymentTypeService.Instance.GetPaymentTypeList(model.SearchCondition);
            result.TotalItemCount = result.PaymentTypeList.Count;
            result.PaymentTypeList = result.PaymentTypeList.Any()
                    ? result.PaymentTypeList.OrderByDescending(x => x.PaymentTypeId).Skip(model.SearchCondition.PageSize * (model.SearchCondition.PageNo - 1))
                        .Take(model.SearchCondition.PageSize)
                        .ToList() : new List<BizPaymentType>();

            result.PageNo = model.SearchCondition.PageNo;
            result.PageSize = model.SearchCondition.PageSize;

            response.Data = result;

            return Json(response);
        }

    }
}
