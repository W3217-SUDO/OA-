using System;
using System.Collections.Generic;
using System.Configuration;
using System.IO;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseTrademarkOfficeFeeController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseTrademarkOfficeFeeController");


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult List(string id)
        {
            var model = new CaseFeeFileListModel();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            model.SearchCondition.CaseClassTypeId = (int)CaseClassType.TradeCopyright;

            return View("List", model);
        }
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult CaseFeeFileSearchList(CaseFeeFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizCaseFeeSearchResultInfo();

                result.CaseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeFileSearchService.Instance.GetCaseFeeFileList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                //Logger.Error("CasePatentOfficeInvoiceFileController.CasePatentOfficeFiles", ex);
            }
            return Json(response);
        }


    }
}
