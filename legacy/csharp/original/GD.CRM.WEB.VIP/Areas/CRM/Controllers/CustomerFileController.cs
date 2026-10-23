using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.Customer.File;
using Dchien.Legal.Web.Areas.CRM.ViewModels.CustomerFile;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CRM.Controllers
{
    [CheckUserLogin]
    public class CustomerFileController : Controller
    {
        internal Log Logger = new Log("CRM.Controllers.CustomerFileController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerGuid"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CustomerFileUpload(string customerGuid)
        {
            var model = new CustomerFileUpload();
            model.CustomerGuid = customerGuid;

            return PartialView("CustomerFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CustomerFileUploading(CustomerFileUpload model)
        {
            var response = this.CheckCustomerFileUploading();

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

            var customerFile = new BizCustomerFile();
            customerFile.CustomerGuid = model.CustomerGuid;
            customerFile.IsLicense = model.IsLicense;
            customerFile.FileName = file.FileName;

            var result = CustomerService.Instance.CreateNewCustomerFile(customerFile, bytes);

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

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckCustomerFileUploading()
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
        /// <param name="customerFileId"></param>
        /// <returns></returns>
        public ActionResult CustomerFileDownload(long customerFileId)
        {
            try
            {
                var customerFile = CustomerFileService.Instance.GetCustomerFile(customerFileId);

                if (customerFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(customerFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =  FileHelper.ReadFile(Path.Combine(FileHelper.CustomerFiles, customerFile.CustomerGuid, customerFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + customerFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"CustomerFileController.CustomerFileDownload","CustomerFileController.CustomerFileDownload", ex);
                throw ex;
            }


            return null;
        }

        /// <summary>
        /// 合同文件下载
        /// </summary>
        /// <param name="customerFileGuid"></param>
        /// <returns></returns>
        public ActionResult CustomerFileDownloadByGuid(string customerFileId)
        {
            try
            {
                var customerFile = CustomerFileService.Instance.GetCustomerFile(customerFileId);

                if (customerFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(customerFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var bytes =
                        FileHelper.ReadFile(Path.Combine(FileHelper.CustomerFiles, customerFile.CustomerGuid, customerFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + customerFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CustomerFileController.CustomerFileDownloadByGuid", "CustomerFileController.CustomerFileDownloadByGuid", ex);
            }

            return null;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult CustomerFileList()
        {
            var model = new CustomerFileListModel();

            return PartialView("CustomerFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult ViewCustomerFileList()
        {
            var model = new CustomerFileListModel();

            return PartialView("View/CustomerFileList", model);
        }
       
        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerGuid"></param>
        /// <returns></returns>
        public JsonResult CustomerFiles(string customerGuid)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            var customerFiles = new List<BizCustomerFile>();

            if (!string.IsNullOrEmpty(customerGuid))
            {
                customerFiles = CustomerFileService.Instance.GetCustomerFileList(customerGuid);
            }

            response.IsSuccess = true;
            response.Data = customerFiles;

            return Json(response);
        }

    }
}
