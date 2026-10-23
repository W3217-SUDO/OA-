using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.BizModel.AWS.OfficialDocument;
using Dchien.Legal.Service.AWS.OfficialDocument;
using Dchien.Legal.Service.AWS.OfficialDocument.File;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentFile;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument;

namespace Dchien.Legal.Web.Areas.AWS.Controllers
{
    
    public class OfficialDocumentFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.OfficialDocumentFileController");


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
                bool result = OfficialDocumentFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "OfficialDocumentFileController.Delete", "OfficialDocumentFileController.Delete", ex);
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
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        public ActionResult FileList(string id, string officialDocumentGuid)
        {
            var model = new FileListModel();
            model.Files = OfficialDocumentFileService.Instance.GetOfficialDocumentFileList(officialDocumentGuid);
            return PartialView("PartialView/FileList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult OfficialDocumentFiles(string officialDocumentGuid, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var officialDocumentFiles = new List<BizOfficialDocumentFile>();

            if (!string.IsNullOrEmpty(officialDocumentGuid))
            {
                officialDocumentFiles = OfficialDocumentFileService.Instance.GetOfficialDocumentFileList(officialDocumentGuid);
            }

            var result = new BizOfficialDocumentFileSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = officialDocumentFiles.Count;

            result.OfficialDocumentFileList = officialDocumentFiles.Any()
                    ? officialDocumentFiles.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.FileId)
                        .ToList()
                    : new List<BizOfficialDocumentFile>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult OfficialDocumentFileUpload(OfficialDocumentModel model)
        {
            var response = new PostResponse();
            var lst = new List<BizOfficialDocumentFile>();
            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }
                var officialDocumentFile = new BizOfficialDocumentFile();
                officialDocumentFile.Uploader = LoginHelper.GetUserName();
                officialDocumentFile.FileName = file.FileName;
                officialDocumentFile.FileSize = fileSize;
                officialDocumentFile.FileGuid = Guid.NewGuid().ToString();
                officialDocumentFile.OfficialDocumentGuid = model.OfficialDocument.Basic.OfficialDocumentGuid;
                officialDocumentFile.UploadTime = DateTime.Now;
                OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes);
                lst.Add(officialDocumentFile);
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
        public ActionResult OfficialDocumentFileDownload(long officialDocumentFileId)
        {
            try
            {
                var officialDocumentFile = OfficialDocumentFileService.Instance.GetOfficialDocumentFile(officialDocumentFileId);

                if (officialDocumentFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(officialDocumentFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var path = Path.Combine(FileHelper.OfficialDocumentFiles, officialDocumentFile.OfficialDocumentGuid, officialDocumentFile.FileName);
                    var bytes = FileHelper.ReadFile(path);
                       

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }
                    return File(bytes, "attachment;filename=" + officialDocumentFile.FileName);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "OfficialDocumentFileController.OfficialDocumentFileDownload", "OfficialDocumentFileController.OfficialDocumentFileDownload", ex);
            }

            return null;
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult ExportTempFileDownload(string fileName)
        {

            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("gb2312");
            Response.ContentType = "application/vnd.ms-word";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                         HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));
            return File(bytes, "attachment;filename=" + fileName);

        }
    }
}
