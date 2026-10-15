using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;

using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.CIT.ViewModels.Investigation;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Investigation;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Web.Areas.CIT.ViewModels.Investigation.File;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationFileController");
 

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult InvestigationFileUpload(InvestigationModel model)
        {
            var response = new PostResponse();

            var lst = new List<BizInvestigationFile>();

            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

                var investigationFile = new BizInvestigationFile();
                investigationFile.FileTypeId = (int)FileType.FileType_10000001;
                investigationFile.UploadingUser = LoginHelper.GetUserName();
                investigationFile.FileName = file.FileName;
                investigationFile.FileSize = fileSize;
                investigationFile.InvestigationGuid = model.Investigation.Basic.InvestigationGuid;
                investigationFile.UploadingTime = DateTime.Now;

                InvestigationFileService.Instance.CreateUpdate(investigationFile, bytes);

                lst.Add(investigationFile);
            }

            response.Message = "上传成功！";
            response.Data = lst;
            response.IsSuccess = true;
 
            return Json(response);
        }


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
                bool result = InvestigationFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationFileController.Delete", "InvestigationFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string investigationNo)
        {
            var model = new FileListModel();
            model.PageSize = 15;
            model.PageNo = 1;

            var investigation = InvestigationService.Instance.GetInvestigation(investigationNo);
            model.BusinessOwner = investigation.Basic.BusinessOwner;

            return PartialView("FileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationGuid"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        public JsonResult InvestigationFiles(string investigationGuid, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationFiles = new List<BizInvestigationFile>();

            if (!string.IsNullOrEmpty(investigationGuid))
            {
                investigationFiles = InvestigationFileService.Instance.GetInvestigationFileList(investigationGuid);
            }

            var result = new BizInvestigationFileSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationFiles.Count;

            result.InvestigationFiles = investigationFiles.Any()
                    ? investigationFiles.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.FileId)
                        .ToList()
                    : new List<BizInvestigationFile>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult FileUpload(string investigationGuid)
        {
            var model = new InvestigationModel();
            model.Investigation = new BizInvestigation();
            model.Investigation.Basic = new BizInvestigationBasic();
            model.Investigation.Basic.InvestigationGuid = investigationGuid;

            return PartialView("PartialView/FileUpload", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationFileDownload(long fileId)
        {
            try
            {
                var investigationFile = InvestigationFileService.Instance.GetInvestigationFile(fileId);

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
                    var path = Path.Combine(FileHelper.InvestigationFiles, investigationFile.InvestigationGuid, investigationFile.FileName);
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationFileController.InvestigationFileDownload", "InvestigationFileController.InvestigationFileDownload", ex);
            }

            return null;
        }

    }
}
