using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel.Lawsuit.Court;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Court;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseCourtController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseCourtController");

        [HttpPost]
        public ActionResult CaseCourtSelected(long caseId)
        {
            var model = new CaseCourtSelectedModel();
            model.CaseId = caseId;

            return PartialView("CaseCourtSelected", model);
        }


        [HttpPost]
        public JsonResult CaseCourtList(CaseCourtSelectedModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                var result = new BizCourtSearchResultInfo();

                result.Courts = CourtService.Instance.GetCourts(model.SearchCondition);

                //result.SelectedCourts =
                //    CaseService.Instance.GetCaseCourts(model.CaseId).Select(x => x.CourtId).ToList();

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错。";
            }
            return Json(response);
        }

    }
}
