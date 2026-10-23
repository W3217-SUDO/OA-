using System;
using System.Web.Mvc;
using System.Text;
using System.IO;
using System.Collections.Generic;

using Dchien.ServiceStack.Common;
using Dchien.ServiceStack.Common.Extensions;
using Dchien.Legal.Common;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseList;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.ServiceStack.Text;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseListController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseListController");

        /// <summary>
        /// /
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult List(string id,int? caseTypeId,string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 10;
            model.SearchCondition.PageId = id;

            if (caseTypeId.HasValue)
            {
                model.SearchCondition.CaseTypeId = caseTypeId.ToString();
            }
            else
            {
                model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();

            }

            model.SearchCondition.Keyword = k;

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104030)
            {
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104040)
            {
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022);

                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104050)
            {
                // 等待上诉
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104060)
            {
                // 等待执行
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020.ToDescription());
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();
            }

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        public ActionResult ScheduleList(string id, string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            //model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();

            model.SearchCondition.Keyword = k;
            model.SearchCondition.Sorting = "T.LawfulDay";

            model.SearchCondition.LawfulDayFrom = DateTime.Now.Date;

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104030)
            {
                model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104040)
            {
                model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022);

                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104050)
            {
                model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
                // 等待上诉
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104060)
            {
                // 等待执行
                model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020.ToDescription());
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();
            }

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetCaseListByCaseNos(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                var caseList = CaseService.Instance.GetCaseBasicListByCaseNos(caseNos);

                response.IsSuccess = true;
                response.Data = new { CaseList = caseList };

            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "获取出错.";
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
        public JsonResult CaseSearchList(CaseListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 10;

                var result = new Dchien.Legal.BizModel.Legal.Case.BizCaseSearchResultInfo();

                result.CaseList = CaseSearchService.Instance.GetCaseList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";

                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseSearchService.Instance.GetCaseList", model.SearchCondition.ToJson(), ex);

            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseListExportToExcel(CaseListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;
            var caseList = CaseSearchService.Instance.GetCaseList(model.SearchCondition);
            var fileName = CaseService.Instance.CaseListExportToExcel(caseList);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNos"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseListSelectedExportToExcel(List<string> caseNos)
        {
            var caseList = CaseService.Instance.GetCaseBasicListByCaseNos(caseNos);
            var fileName = CaseService.Instance.CaseListExportToExcel(caseList);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        [HttpPost]
        public ActionResult CaseListExportToExcelForManifest(List<string> caseNos)
        {
            var caseList = CaseService.Instance.GetCaseBasicListByCaseNos(caseNos);
            var fileName = CaseService.Instance.CaseListExportToExcelForManifest(caseList);

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
        public ActionResult CaseListExportToExcelDownload(string fileName)
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


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="k"></param>
        /// <returns></returns>
        public ActionResult SelectedList(string id, string k)
        {
            var model = new CaseListModel();
            model.SearchCondition = new CaseSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 10;
            model.SearchCondition.PageId = id;
            model.SearchCondition.CaseTypeId = ((int)CaseType.CaseType_110).ToString();

            model.SearchCondition.Keyword = k;
            model.SearchCondition.Sorting = "T.LawfulDay";

            model.SearchCondition.LawfulDayFrom = DateTime.Now.Date;

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104030)
            {
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101015.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102013.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_103012.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104040)
            {
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022);
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022);

                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101022.ToDescription());
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102022.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104050)
            {
                // 等待上诉
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101019.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();

            }

            if (model.SearchCondition.PageId == Entity.System.PageId.PageId_1001104060)
            {
                // 等待执行
                var casePhases = new List<int>();
                var casePhaseNames = new List<string>();

                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_101020.ToDescription());
                casePhases.Add((int)Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017);
                casePhaseNames.Add(Dchien.Legal.Entity.BAS.Type.CasePhaseType.Phase_102017.ToDescription());

                model.SearchCondition.CasePhaseId = string.Join(",", casePhases);
                model.SearchCondition.CasePhaseName = string.Join(",", casePhaseNames);

                model.SearchCondition.UserId = LoginHelper.GetUserName();
            }

            model.SearchCondition.AccessLevel = (Entity.Account.AccessLevel)LoginHelper.GetAccesslevel();
            model.SearchCondition.UserId = LoginHelper.GetUserName();

            return View(model);
        }

    }
}
