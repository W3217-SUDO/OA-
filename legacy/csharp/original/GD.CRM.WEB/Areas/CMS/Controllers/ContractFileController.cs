using System;
using System.IO;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using Dchien.Legal.BizModel.CMS.Contract;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.CMS.Contract;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CMS.Contract;
using Dchien.Legal.Service.CMS.Contract.File;
using Dchien.Legal.Web.Areas.CMS.ViewModels.Contract;
using Dchien.Legal.Web.Areas.CMS.ViewModels.ContractFile;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.CMS.Controllers
{
    [CheckUserLogin]
    public class ContractFileController : Controller
    {
        internal Log Logger = new Log("CMS.Controllers.ContractFileController");


        /// <summary>
        /// 
        /// </summary>
        /// <param name="contractId"></param>
        /// <param name="contractNo"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult ContractFileUpload(long contractId,string contractNo)
        {
            var model = new ContractFileUpload();
            model.ContractId = contractId;
            model.ContractNo = contractNo;

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
            contractFile.ContractId = model.ContractId;
            contractFile.ContractNo = model.ContractNo;

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
                        FileHelper.ReadFile(Path.Combine(FileHelper.ContractFiles, contractFile.ContractNo, contractFile.FileName));

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }

                    return File(bytes, "attachment;filename=" + contractFile.FileName);
                }

            }
            catch (Exception ex)
            {
                Logger.Error("ContractFileController.ContractFileDownload", ex);
                throw ex;
            }


            return null;
        }

    }
}
