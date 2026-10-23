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
using Dchien.Legal.Entity.FIO.PatentOfficeInvoice;
using Dchien.Legal.BizModel.FIO.PatentOfficeInvoice;
using Dchien.Legal.Service.FIO.PatentOfficeInvoice;
using System.Web;

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class PatentOfficeInvoiceFileController : BaseController
    {
        internal Log Logger = new Log("FIO.Controllers.PatentOfficeInvoiceFileController");

        #region 专利票据文件批量文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>

        public ActionResult PatentOfficeInvoiceFileImport(string id)
        {
            var model = new PatentOfficeInvoiceFileImportModel();

            return View("PatentOfficeInvoiceFileImport", model);
        }

        /// <summary>
        /// 案件批量上传并导入
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileUpload()
        {
            var response = new PostResponse();

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return Json(response);
            }

            int fileLen = file.ContentLength;

            Stream stream;
            byte[] bytes = new byte[fileLen];
            stream = file.InputStream;
            stream.Read(bytes, 0, fileLen);

            var metaFile = new BizOfficeMetaFile()
            {
                FileGuid = Guid.NewGuid(),
                FileName = Path.GetFileNameWithoutExtension(file.FileName),
                FileExtension = Path.GetExtension(file.FileName)
            };

            try
            {
                OfficeMetaFileService.Instance.CreateInvoiceFile(metaFile, bytes);

                PatentOfficeInvoiceFileService.Instance.ProcessPatentOfficeMetaFile(metaFile, bytes);
                var invoiceFiles = PatentOfficeInvoiceFileService.Instance.GetPatentOfficeInvoiceFileList(metaFile.FileGuid.ToString());
                response.Data = invoiceFiles;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeInvoiceFileUploading", "PatentOfficeInvoiceFileUploading", ex);
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return new JsonResult()
            {
                Data = response,
                MaxJsonLength = int.MaxValue,
                ContentType = "application/json"
            };

            //return Json(response);

        }

        #endregion 

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetPatentOfficeInvoiceFileList(PatentOfficeInvoiceFileListModel model)
        {
            var response = new PostResponse();

            if (model.SearchCondition.PageId == PageId.PageId_1101007004)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1101007008)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }

            try
            {
                var invoiceFiles = Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.GetPatentOfficeInvoiceFileList(model.SearchCondition);

                if (invoiceFiles != null && invoiceFiles.Any())
                {
                    var result = new BizPatentOfficeInvoiceFileResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.InvoiceFiles = invoiceFiles;
                    response.Data = result;

                    response.IsSuccess = true;
                }
                else
                {
                    response.IsSuccess = false;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.PatentOfficeInvoiceFileList", "PatentOfficeController.PatentOfficeInvoiceFileList", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #region 专利官费票据业务处理

        public ActionResult PatentOfficeInvoiceFileBusinessProcessList(string id)
        {
            var model = new PatentOfficeInvoiceFileListModel();
            model.SearchCondition = new PatentOfficeInvoiceFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;

            return View("PatentOfficeInvoiceFileBusinessProcessList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileBusinessProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileBusinessProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileBusinessProcess", "PatentOfficeInvoiceFileBusinessProcess.PatentOfficeFileBusinessProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileBusinessOnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileBusinessOnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileBusinessOnProcess", "PatentOfficeFileController.PatentOfficeInvoiceFileBusinessOnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileBusinessUnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileBusinessUnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileBusinessUnProcess", "PatentOfficeFileController.PatentOfficeInvoiceFileBusinessUnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 专利官费票据流程处理

        public ActionResult PatentOfficeInvoiceFileServiceProcessList(string id)
        {
            var model = new PatentOfficeInvoiceFileListModel();
            model.SearchCondition = new PatentOfficeInvoiceFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            return View("PatentOfficeInvoiceFileServiceProcessList", model);
        }


        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileServiceProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileServiceProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileServiceProcess", "PatentOfficeFileController.PatentOfficeInvoiceFileServiceProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileServiceOnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileBusinessOnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileServiceOnProcess", "PatentOfficeFileController.PatentOfficeInvoiceFileServiceOnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileServiceUnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PatentOfficeInvoice.PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileServiceUnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeInvoiceFileController.PatentOfficeInvoiceFileServiceUnProcess", "PatentOfficeFileController.PatentOfficeInvoiceFileServiceUnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 打包下载


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officeFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeInvoiceFilePacking(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                var fileList = PatentOfficeInvoiceFileService.Instance.GetPatentOfficeInvoiceFileList(officeFileIds.ToList());

                var files = new List<string>();

                fileList.ForEach(x =>
                {
                    files.Add(Path.Combine(FileHelper.PatentOfficeInvoiceFiles, x.MetaFileGuid, x.InvoiceFileName));

                    var originalPath = Path.Combine(FileHelper.PatentOfficeFiles, x.MetaFileGuid, x.InvoiceFileName);
                    var destinationPath = Path.Combine(FileHelper.ExportTempFiles, x.MetaFileGuid, x.InvoiceFileName);

                    FileHelper.CopyFile(destinationPath, originalPath);

                    files.Add(destinationPath);
                });

                if (files.Any())
                {
                    var fileName = Guid.NewGuid() + ".zip";
                    FileHelper.CreateZipFile(files.ToArray(), Path.Combine(FileHelper.ExportTempFiles, fileName), string.Empty);
                    response.Data = fileName;
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFilePacking", "PatentOfficeFileController.PatentOfficeInvoiceFilePacking", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        public ActionResult PatentOfficeInvoiceFileDownload(string fileName)
        {
            try
            {
                // 设置编码和附件格式  
                Response.Charset = "gb2312";
                Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                //Response.ContentType = "application/vnd.ms-word";

                Response.AppendHeader("Content-Disposition", "attachment;filename=" + HttpUtility.UrlEncode(fileName, Encoding.UTF8).ToString());

                // 返回客户端  
                var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));

                if (bytes == null)
                {
                    bytes = new byte[0];
                }

                return File(bytes, "attachment;filename=" + fileName);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeInvoiceFileController.PatentOfficeInvoiceFileDownload", "PatentOfficeInvoiceFileController.PatentOfficeInvoiceFileDownload", ex);
                throw ex;
            }

         }

        #endregion

        #region 页面导出

        /// <summary>
        /// 专利文件导出
        /// </summary>
        /// <param name="search"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult PatentOfficeFileListExportToExcel(long[] officeFileIds)
        {
            var invoiceFiles = PatentOfficeInvoiceFileService.Instance.GetPatentOfficeInvoiceFileList(officeFileIds.ToList());
            var fileName = PatentOfficeInvoiceFileService.Instance.PatentOfficeInvoiceFileListExportToExcel(invoiceFiles);
            var response = new PostResponse();
            response.IsSuccess = true;
            response.Data = fileName;
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileName"></param>
        /// <returns></returns>
        public ActionResult PatentOfficeFileListExportToExcelDownload(string fileName)
        {
            // 设置编码和附件格式  
            Response.Charset = "gb2312";
            Response.ContentEncoding = Encoding.GetEncoding("GB2312");
            Response.ContentType = "application/vnd.ms-excel";

            Response.AppendHeader("Content-Disposition", "attachment;filename=" + fileName );

            // 返回客户端  
            var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ExportTempFiles, fileName));

            return File(bytes, "attachment;filename=" + fileName);
        }

        #endregion

        #region 页面导入

        [HttpPost]
        public JsonResult PatentOfficeInvoiceFileIn(BizPatentOfficeInvoiceFile[] invocieFiles)
        {
            var response = new PostResponse();

            try
            {
                var files = PatentOfficeInvoiceFileService.Instance.ProcessPatentOfficeInvoiceFile(invocieFiles.ToList());
                response.IsSuccess = true;
                response.Message = string.Format("成功导入{0}文件", files.FindAll(x=>!x.HasError).Count);
                response.Data = files.FindAll(x => !x.HasError).Select(x=>x.FileId.ToString());

                if (files.FindAll(x => x.HasError).Count > 0)
                {
                    response.Message = string.Join("<br>", files.FindAll(x => x.HasError).Select(x=>x.ErrorMessage).ToList());
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeInvoiceFileIn", "PatentOfficeFileController.PatentOfficeInvoiceFileIn", ex);
                response.IsSuccess = false;
                response.Message = "导入文件出错.";
            }

            return Json(response);
        }
        #endregion

        #region 专利官费票据未导入处理

        public ActionResult PatentOfficeInvoiceFileUnProcessList(string id)
        {
            var model = new PatentOfficeInvoiceFileListModel();
            model.SearchCondition = new PatentOfficeInvoiceFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            model.SearchCondition.Status = (int)PatentOfficeInvoiceFileStatus.UnImported;
            return View("PatentOfficeInvoiceFileUnProcessList", model);
        }

 
        #endregion

    }
}
