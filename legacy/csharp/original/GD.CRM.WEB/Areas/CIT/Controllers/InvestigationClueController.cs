using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Text;
using System.IO;
using System.Threading;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationClueController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string id)
        {
            var model = new InvestigationClueListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;
            return View("List", model);
        }

        [HttpPost]
        [CheckUserLogin]
        public JsonResult List(InvestigationClueListModel model)
        {
            var response = new PostResponse();
            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;
                var result = new BizInvestigationClueSearchResultInfo();
                result.InvestigationClues = InvestigationClueService.Instance.GetInvestigationClueList(model.SearchCondition);
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
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvestigationClueListAllExportToExcel(InvestigationClueListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            var clues = InvestigationClueService.Instance.GetInvestigationClueList(model.SearchCondition);
            var fileName = InvestigationClueService.Instance.InvestigationClueListSelectedExportToExcel(clues);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueGuids"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvestigationClueListSelectedExportToExcel(List<string> investigationClueGuids)
        {
            var clues = InvestigationClueService.Instance.GetInvestigationClueList(investigationClueGuids);
            var fileName = InvestigationClueService.Instance.InvestigationClueListSelectedExportToExcel(clues);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvestigationClueListAllExportToExcelForManifest(InvestigationClueListModel model)
        {
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 60000;

            var clues = InvestigationClueService.Instance.GetInvestigationClueList(model.SearchCondition);
            var fileName = InvestigationClueService.Instance.InvestigationClueListExportToExcelForManifest(clues);

            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = Path.GetFileNameWithoutExtension(fileName);
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueGuids"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult InvestigationClueListSelectedExportToExcelForManifest(List<string> investigationClueGuids)
        {
            var clues = InvestigationClueService.Instance.GetInvestigationClueList(investigationClueGuids);
            var fileName = InvestigationClueService.Instance.InvestigationClueListExportToExcelForManifest(clues);

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
        public ActionResult InvestigationClueListExportToExcelDownload(string fileName)
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
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult ClueList()
        {
            var model = new InvestigationClueListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            return PartialView("PartialView/ClueList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult InvestigationClues(string investigationTaskNo, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationClues = new List<BizInvestigationClue>();

            if (!string.IsNullOrEmpty(investigationTaskNo))
            {
                investigationClues = InvestigationClueService.Instance.GetInvestigationClueList(investigationTaskNo);
            }

            var result = new BizInvestigationClueSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationClues.Count;

            result.InvestigationClues = investigationClues.Any()
                    ? investigationClues.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.Basic.ClueId)
                        .ToList()
                    : new List<BizInvestigationClue>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Clue(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClue(investigationClueNo);
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(model.InvestigationClue.Basic.InvestigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            return PartialView("PartialView/Clue", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult ClueView(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClue(investigationClueNo);
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(model.InvestigationClue.Basic.InvestigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);

            return PartialView("PartialView/ClueView", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Create(string id, string investigationTaskNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(investigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);
            model.InvestigationClue = new BizInvestigationClue();
            model.InvestigationClue.Basic = new BizInvestigationClueBasic();
            model.InvestigationClue.Basic.InvestigationTaskNo = model.InvestigationTask.Basic.TaskNo;
            model.InvestigationClue.Basic.InvestigationNo = model.Investigation.Basic.InvestigationNo;
            model.InvestigationClue.Basic.InvestigationDate = DateTime.Now;

            return PartialView("PartialView/CreateUpdate", model);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult ClueCreate(string id, string investigationTaskNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationTask = InvestigationTaskService.Instance.GetInvestigationTask(investigationTaskNo);
            model.Investigation = InvestigationService.Instance.GetInvestigation(model.InvestigationTask.Basic.InvestigationNo);
            model.InvestigationClue = new BizInvestigationClue();
            model.InvestigationClue.Basic = new BizInvestigationClueBasic();
            model.InvestigationClue.Basic.ClueGuid = Guid.NewGuid().ToString();
            model.InvestigationClue.Basic.InvestigationTaskNo = model.InvestigationTask.Basic.TaskNo;
            model.InvestigationClue.Basic.InvestigationNo = model.Investigation.Basic.InvestigationNo;

            model.InvestigationClue.Basic.InvestigationDate = DateTime.Now;

            return PartialView("PartialView/ClueCreate", model);
        }


        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public ActionResult ClueEdit(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);

            return PartialView("PartialView/ClueEdit", model);
        }


        [HttpPost]
        public JsonResult Delete(List<string> clueNos)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvestigationClueService.Instance.Delete(clueNos);

                if (result)
                {
                    response.Message = "删除成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "删除失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueController.Delete", "InvestigationClueController.Delete", ex);
                throw;
            }

            return Json(response);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult InvestigationClueCreate(InvestigationClueCreateModel request,bool needToAudit)
        {
            var response = new PostResponse();
            InvestigationClueService.Instance.Create(request.InvestigationClue, 
                request.InvestigationClueProduct, 
                request.InvestigationClueIndicteeList, 
                request.InvestigationClueProducerList,
                needToAudit);
            response.Message = "新增线索成功！";
            response.IsSuccess = true;
            return Json(response);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult InvestigationClueUpdate(InvestigationClueCreateModel request, bool needToAudit)
        {
            var response = new PostResponse();

            InvestigationClueService.Instance.Update(request.InvestigationClue, 
                request.InvestigationClueProduct, 
                request.InvestigationClueIndicteeList, 
                request.InvestigationClueProducerList,
                needToAudit);

            response.Message = "修改线索成功！";
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="indicterNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetInvestigationClueListByIndicterNo(string indicterNo)
        {
            var response = new PostResponse();

            try
            {
                var investigationClueList = InvestigationClueService.Instance.GetNotUsedInvestigationClueListByIndicterNo(indicterNo);
                response.IsSuccess = true;
                response.Data = investigationClueList;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueController.GetInvestigationClueListByIndicterNo", "InvestigationClueController.GetInvestigationClueListByIndicterNo", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetInvestigationClue(string investigationClueNo)
        {
            var response = new PostResponse();

            try
            {
                var investigationClue = InvestigationClueService.Instance.GetInvestigationClue(investigationClueNo);
                response.Data = investigationClue;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueController.GetInvestigationClueListByIndicterNo", "InvestigationClueController.GetInvestigationClueListByIndicterNo", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        #region 生成案件

        /// <summary>
        /// /
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ClueGenerateCase(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);
            return PartialView("PartialView/ClueGenerateCase", model);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        private bool CheckFileType(string fileName)
        {
            //FileName为空时不验证 图片格式 修改图片适用
            if (string.IsNullOrEmpty(fileName))
                return true;

            var start = fileName.LastIndexOf(".");
            string type = fileName.Substring(start, fileName.Length - start);
            //if (type.ToLower() == ".jpg" || type.ToLower() == ".png" || type.ToLower() == ".gif")
            //    return true;

            //return false;

            return true;

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckFileUploading()
        {
            var response = new PostResponse();

            if (Request.Files == null || Request.Files.Count == 0)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return response;
            }

            if (file.ContentLength == 0)
            {
                response.Message = "文件没有任何内容.";
                response.IsSuccess = false;
                return response;
            }

            if (!CheckFileType(file.FileName))
            {
                response.Message = "上传文件类型不正确,上传失败！";
                response.IsSuccess = false;
                return response;
            }

            return null;

        }

        #region 导入线索
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult InvestigationClueFileUpload()
        {
            return View("InvestigationClueFileUpload");
        }

        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueInFileUpload()
        {
            var response = this.CheckFileUploading();
            if (response != null)
            {
                return Json(response);
            }
            response = new PostResponse();
            var file = Request.Files[0];
            int fileSize = file.ContentLength;
            var bytes = new byte[fileSize];
            using (var stream = file.InputStream)
            {
                stream.Read(bytes, 0, fileSize);
            }
            try
            {
                var lst = InvestigationClueService.Instance.Process(file.FileName, bytes);
                if (lst != null && lst.Any())
                {
                    lst.ForEach(x =>
                    {
                        InvestigationClueService.Instance.Create(x.Basic,x.Product,x.InvestigationClueIndicteeList,x.InvestigationClueProducerList,true);
                        //Thread.Sleep(3000);
                    });
                    response.Data = new { InvestigationClues = lst, PrimaryFileName = file.FileName };
                    response.Message = "导入成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "导入失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueEvidenceController.InvestigationClueEvidenceAddInFileUpload", "InvestigationClueEvidenceController.InvestigationClueEvidenceAddInFileUpload", ex);
                response.Message = "文件格式不正确.";
                response.IsSuccess = false;
            }
            return Json(response);
        }

        #endregion

        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public ActionResult Investigator(string id, string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);

            return PartialView("PartialView/Investigator", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="clueNos"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult UpdateInvestigator(InvestigationClueCreateModel model,List<string> clueNos)
        {
            var response = new PostResponse();

            try
            {
                if (clueNos.Any())
                {
                    clueNos.ForEach(clueNo =>
                    {
                        model.InvestigationClue.ClueNo = clueNo;
                        response.IsSuccess = InvestigationClueService.Instance.UpdateInvestigator(model.InvestigationClue);
                    });
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueController.UpdateInvestigator", "InvestigationClueController.UpdateInvestigator", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="clueNos"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult UpdateCluePaymentStatus(List<string> clueNos)
        {
            var response = new PostResponse();

            try
            {
                if (clueNos.Any())
                {
                    response.IsSuccess = InvestigationClueService.Instance.UpdateCluePaymentStatus(clueNos);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueController.UpdateCluePaymentStatus", "InvestigationClueController.UpdateCluePaymentStatus", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        [CheckUserLogin]
        public ActionResult MultiCreate(int feeTypeId, string caseNos)
        {
            ViewBag.FeeTypeId = feeTypeId;

            return PartialView("PartialView/MultiCreate");
        }

    }
}
