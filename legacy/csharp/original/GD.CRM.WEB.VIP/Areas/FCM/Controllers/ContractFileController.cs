using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.FCM.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.FCM.Contract.File;
using Dchien.Legal.Web.Areas.FCM.ViewModels.ContractFile;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.FCM.Controllers
{
    [CheckUserLogin]
    public class ContractFileController : Controller
    {
        internal Log Logger = new Log("FCM.Controllers.ContractFileController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractFileUpload(string contractGuid)
        {
            var model = new ContractFileUpload();
            model.ContractGuid = contractGuid;

            return PartialView("ContractFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult ContractFileUploading(ContractFileUpload model)
        {
            var response = this.CheckContractFileUploading();

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

            var contractFile = new BizContractFile();
            contractFile.ContractGuid = model.ContractGuid;
            contractFile.FileName = file.FileName;

            var result = ContractService.Instance.CreateNewContractFile(contractFile, bytes);

            if (result)
            {
                response.Message = "上传成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }


        [HttpPost]
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult DarftContractFileUpload(string contractGuid)
        {
            var response = new PostResponse();

            var lst = new List<BizContractFile>();

            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

                var contractFile = new BizContractFile();
                contractFile.ContractGuid = contractGuid;
                contractFile.UploadUser = LoginHelper.GetUserName();
                contractFile.FileName = DateTime.Now.ToString("yyyyMMddHHmmssfff") + "_" + file.FileName;
                contractFile.FileSize = fileSize;
                contractFile.UploadTime = DateTime.Now;

                var result = ContractService.Instance.CreateNewContractFile(contractFile, bytes);
                 
                lst.Add(contractFile);
            }

            response.Message = "上传成功！";
            response.Data = lst;
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckContractFileUploading()
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
        /// 合同文件下载
        /// </summary>
        /// <param name="contractFileId"></param>
        /// <returns></returns>
        public ActionResult ContractFileDownload(long contractFileId)
        {
            try
            {
                var contractFile = ContractFileService.Instance.GetContractFile(contractFileId);

                if (contractFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(contractFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.ContractFiles, contractFile.ContractGuid, contractFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + contractFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"ContractFileController.ContractFileDownload","ContractFileController.ContractFileDownload", ex);
                throw ex;
            }


            return null;
        }

        /// <summary>
        /// 合同文件下载
        /// </summary>
        /// <param name="contractFileGuid"></param>
        /// <returns></returns>
        public ActionResult ContractFileDownloadByGuid(string contractFileGuid)
        {
            try
            {
                var contractFile = ContractFileService.Instance.GetContractFile(contractFileGuid);

                if (contractFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(contractFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var path = Path.Combine(FileHelper.ContractFiles, contractFile.ContractGuid, contractFile.FileName);
                    var bytes =
                        FileHelper.ReadFile(path);

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }
                    return File(bytes, "attachment;filename=" + contractFile.FileName);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractFileController.ContractFileDownload", "ContractFileController.ContractFileDownload", ex);
            }

            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ContractFileList()
        {
            var model = new ContractFileListModel();

            return PartialView("ContractFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ViewContractFileList()
        {
            var model = new ContractFileListModel();

            return PartialView("View/ContractFileList", model);
        }
       
        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractGuid"></param>
        /// <returns></returns>
        public JsonResult ContractFiles(string contractGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var contractFiles = new List<BizContractFile>();

            if (!string.IsNullOrEmpty(contractGuid))
            {
                contractFiles = ContractFileService.Instance.GetContractFileList(contractGuid);
            }

            response.IsSuccess = true;
            response.Data = contractFiles;

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <returns></returns>

        [CheckUserLogin]
        public ActionResult ContractFileListOnModal(long contractId)
        {
            var model = new ContractFileListModel();

            model.ContractFiles = ContractFileService.Instance.GetContractFileList(contractId);

            return PartialView("View/ContractFileListOnModal", model);
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
                bool result = ContractFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "ContractFileController.Delete", "ContractFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }

 

    }
}
