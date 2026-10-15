using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue.File;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Service.Legal.Investigation.Clue;


namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    
    public class InvestigationClueFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueFileController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Delete(List<long> fileIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvestigationClueFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueFileController.Delete", "InvestigationClueFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string id)
        {
            var model = new FileListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.PageId = id;
            return PartialView("FileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InvestigationClueFiles(string investigationClueGuid, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationFiles = new List<BizInvestigationClueFile>();

            if (!string.IsNullOrEmpty(investigationClueGuid))
            {
                investigationFiles = InvestigationClueFileService.Instance.GetinvestigationClueFileList(investigationClueGuid);
            }

            var result = new BizInvestigationClueFileSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationFiles.Count;

            result.InvestigationClueFiles = investigationFiles.Any()
                    ? investigationFiles.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.FileId)
                        .ToList()
                    : new List<BizInvestigationClueFile>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult FileUpload(string investigationClueNo)
        {
            var model = new InvestigationClueModel();
            model.InvestigationClue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);

            return PartialView("PartialView/FileUpload", model);
        }

        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult InvestigationClueFileUpload(InvestigationClueModel model)
        {
            var response = new PostResponse();
            var lst = new List<BizInvestigationClueFile>();
            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

                var investigationClueFile = new BizInvestigationClueFile();
                investigationClueFile.FileTypeId = (int)FileType.FileType_10000002;
                investigationClueFile.UploadingUser = LoginHelper.GetUserName();
                investigationClueFile.FileName = file.FileName;
                investigationClueFile.FileSize = fileSize;
                investigationClueFile.ClueGuid = model.InvestigationClue.Basic.ClueGuid;
                investigationClueFile.UploadingTime = DateTime.Now;
                InvestigationClueFileService.Instance.CreateUpdate(investigationClueFile, bytes);
                lst.Add(investigationClueFile);
            }
            response.Data = lst;
            response.Message = "上传成功！";
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationClueFileDownload(long investigationFileId)
        {
            try
            {
                var investigationFile = InvestigationClueFileService.Instance.GetInvestigationClueFile(investigationFileId);

                if (investigationFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(investigationFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var path = Path.Combine(FileHelper.InvestigationClueFiles, investigationFile.ClueGuid, investigationFile.FileName);
                    var bytes =
                        FileHelper.ReadFile(path);

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }
                    return File(bytes, "attachment;filename=" + investigationFile.FileName);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueFileController.InvestigationClueFileDownload", "InvestigationClueFileController.InvestigationClueFileDownload", ex);
            }

            return null;
        }
    }
}
