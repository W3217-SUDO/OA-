using System;
using System.Collections.Generic;
using System.Configuration;
using System.IO;
using System.Linq;
using System.Web.Mvc;

 
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CasePatentOfficeFileController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CasePatentOfficeFileController");


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult List(string id)
        {
            var model = new CaseFileListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;

            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult CaseFileSearchList(CaseFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFileSearchResultInfo();

                result.CaseFileList = CaseFileSearchService.Instance.GetCaseFileList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                //Logger.Error("CasePatentOfficeFileController.CasePatentOfficeFiles", ex);
            }
            return Json(response);
        }


    }
}
