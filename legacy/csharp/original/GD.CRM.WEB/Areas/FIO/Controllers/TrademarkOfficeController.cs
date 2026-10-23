using System;
using System.Collections.Generic;
using System.Text;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FIO;
using Dchien.Legal.BizModel.FIO.PatentOffice;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.FIO;
using Dchien.Legal.Service.FIO.PatentOffice;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.FIO.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Service.FIO.TrademarkOffice;

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class TrademarkOfficeController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.TrademarkOfficeController");

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult TrademarkOfficeFileImport(string id)
        {
            var model = new TrademarkOfficeFileImportModel();
            return View("TrademarkOfficeFileImport", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult TrademarkOfficeFileUploading()
        {
            //var response = new PostResponse();
            try
            {
                var response = this.CheckCaseFileUploading();

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

                var files = TrademarkOfficeService.Instance.ProcessTrademarkOfficeFile(file.FileName, bytes);

                if (files != null && files.Any())
                {
                    response.Data = files;
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
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "TrademarkOfficeController.TrademarkOfficeFileImport", "TrademarkOfficeController.TrademarkOfficeFileImport", ex);
                throw;

            }


        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult TrademarkOfficeFileImport(TrademarkOfficeFileImportModel model)
        {
            var response = new PostResponse();
            try
            {
                
                bool result = CaseFileService.Instance.TrademarkOfficeFileImportProcess(model.TrademarkOfficeFiles);

                if (result)
                {
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "TrademarkOfficeController.TrademarkOfficeFileImport", "TrademarkOfficeController.TrademarkOfficeFileImport", ex);
                throw;
            }

            return Json(response);
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
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckCaseFileUploading()
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
    }
}
