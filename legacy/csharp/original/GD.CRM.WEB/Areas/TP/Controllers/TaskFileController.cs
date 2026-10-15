using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;

using Dchien.Legal.Service.TP.Task;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.TP.ViewModels.Task;
using Dchien.Legal.Entity.System;
using Dchien.Legal.BizModel.TP.Task;
using Dchien.Legal.Service;


namespace Dchien.Legal.Web.Areas.TP.Controllers
{
    [CheckUserLogin]
    public class TaskFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.TaskFileController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult TaskFileUpload(TaskModel model)
        {
            var response = new PostResponse();

            var lst = new List<BizTaskFile>();

            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

                var taskFile = new BizTaskFile();
                taskFile.UploadUser = LoginHelper.GetUserName();
                taskFile.FileName = file.FileName;
                taskFile.FileSize = fileSize;
                taskFile.TaskGuid = model.Task.TaskGuid;
                taskFile.MessageGuid = model.Task.MessageGuid;
                taskFile.UploadTime = DateTime.Now;

                TaskFileService.Instance.CreateUpdate(taskFile, bytes);

                lst.Add(taskFile);

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
        [HttpPost]
        public JsonResult Delete(List<long> fileIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = TaskFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "TaskFileController.Delete", "TaskFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <returns></returns>
        //[CheckUserLogin]
        //public ActionResult List(string id)
        //{
        //    var model = new FileListModel();
        //    model.PageSize = 15;
        //    model.PageNo = 1;
        //    model.PageId = id;
        //    return PartialView("FileList", model);
        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="taskNo"></param>
        ///// <param name="pageNo"></param>
        ///// <param name="pageSize"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public JsonResult TaskFiles(string taskNo, int? pageNo, int? pageSize)
        //{
        //    var response = new PostResponse();

        //    var taskFiles = new List<BizTaskFile>();

        //    if (!string.IsNullOrEmpty(taskNo))
        //    {
        //        taskFiles = TaskFileService.Instance.GettaskFileList(taskNo);
        //    }

        //    var result = new BizTaskFileSearchResultInfo();

        //    result.PageNo = pageNo > 0 ? pageNo.Value : 1;
        //    result.PageSize = pageSize > 0 ? pageSize.Value : 15;

        //    result.TotalItemCount = taskFiles.Count;

        //    result.TaskFiles = taskFiles.Any()
        //            ? taskFiles.Skip(result.PageSize * (result.PageNo - 1))
        //                .Take(result.PageSize)
        //                .OrderBy(x => x.FileId)
        //                .ToList()
        //            : new List<BizTaskFile>();

        //    response.IsSuccess = true;
        //    response.Data = result;

        //    return Json(response);

        //}

        ///// <summary>
        ///// 
        ///// </summary>
        ///// <param name="taskNo"></param>
        ///// <returns></returns>
        //[HttpPost]
        //public ActionResult FileUpload(string taskNo)
        //{
        //    var model = new TaskModel();
        //    model.Task = new BizTask();
        //    model.Task.Basic = new BizTaskBasic();
        //    model.Task.Basic.ClueNo = taskNo;

        //    return PartialView("PartialView/FileUpload", model);
        //}

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult TaskFileDownload(long fileId)
        {
            try
            {
                var taskFile = TaskFileService.Instance.GetTaskFile(fileId);

                if (taskFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(taskFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var path = Path.Combine(FileHelper.TaskFiles, taskFile.TaskGuid, taskFile.FileName);
                    var bytes =
                        FileHelper.ReadFile(path);

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }
                    return File(bytes, "attachment;filename=" + taskFile.FileName);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "TaskFileController.TaskFileDownload", "TaskFileController.TaskFileDownload", ex);
            }

            return null;
        }
    }
}
