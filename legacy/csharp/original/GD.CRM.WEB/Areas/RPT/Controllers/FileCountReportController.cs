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
using Dchien.Legal.Service.IPR.Case;

namespace Dchien.Legal.Web.Areas.RPT.Controllers
{
    [CheckUserLogin]
    public class FileCountReportController : Controller
    {
        internal Log Logger = new Log("RPT.Controllers.FileCountReportController");

        [CheckUserLogin]
        public ActionResult CountFileList(string id)
        {
            var model = new CountFileListModel();

            model.SearchCondition = new Entity.IPR.Case.CaseFileCountSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 2000;

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult FileList(CountFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 2000;

                var lst = CaseFileCountSearchService.Instance.GetCountCaseFileList(model.SearchCondition);

                response.IsSuccess = true;
                response.Data = lst;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "FileCountReportController.FileList", "FileCountReportController.FileList", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


    }
}
