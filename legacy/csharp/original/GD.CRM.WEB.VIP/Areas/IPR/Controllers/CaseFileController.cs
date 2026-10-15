using System;
using System.Collections.Generic;
using System.Configuration;
using System.IO;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.Service;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AR.CaseFee;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.IPR.CaseFileProcess.Patent;
using Dchien.Legal.Service.IPR.CaseFileProcess.Trademark;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.IPR.CaseFileProcess;

namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseFileController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseFileController");

        #region 案件文件批量上传

        /// <summary>
        /// 案件批量修改
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileBatchImport(CaseFileBatchImportModel model)
        {
            model.UploadingTime = DateTime.Now;

            return PartialView("CaseFileBatchImport", model);
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

        /// <summary>
        ///  保存案件批量修改
        /// </summary>
        /// <param name="model"></param>
        /// <param name="caseIdList"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileBatchImportProcess(CaseFileBatchImportModel model, string caseIdList)
        {
            var response = this.CheckCaseFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            if (!model.CaseFileTypeId.HasValue)
            {
                response = new PostResponse();
                response.Message = string.Format("请选择文件类型.");
                response.IsSuccess = false;

                return Json(response);
            }

            var caseFileType = CaseTypeService.Instance.GetAllCaseFileTypes().First(x => x.FileTypeId == model.CaseFileTypeId.Value);

            if (null == caseFileType)
            {
                response = new PostResponse();
                response.Message = string.Format("请选择文件类型.");
                response.IsSuccess = false;

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

            var caseFileList = new List<BizCaseFile>();

            foreach (var caseId in caseIdList.Split(',').Select(x => long.Parse(x)).ToList())
            {
                var c = CaseService.Instance.GetCaseBasic(caseId);

                if (c == null)
                {
                    response.Message = string.Format("案件({0})不存在。", caseId);
                    response.IsSuccess = false;
                    return Json(response);
                }


                var caseFile = new BizCaseFile();
                caseFile.CaseId = c.CaseBasicInfo.CaseId;
                caseFile.CaseNo = c.CaseBasicInfo.CaseNo;
                caseFile.CaseRequestNo = c.CaseBasicInfo.CaseRequestNo;
                caseFile.FileTypeId = model.CaseFileTypeId.Value;
                caseFile.FileTypeName = model.CaseFileTypeName;
                caseFile.FileName = DateTime.Now.ToString("yyyyMMddHHmmss") + "_" + file.FileName;
                caseFile.FileSize = fileSize;
                caseFile.IsActive = true;
                caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;
                caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;

                var canRepeatUpload = CaseFileService.Instance.CheckCaseFileCanRepeatUpload(caseFile);

                if (!canRepeatUpload)
                {
                    response.Message = string.Format("案件({0})已存在该类型文档，且不允许重复上传。", caseFile.CaseNo);
                    response.IsSuccess = false;
                    return Json(response);
                }

                var hedgingFileTypeIds = caseFileType.HedgingFileTypeId;
                var hedgingFeeTypeIds = caseFileType.HedgingFeeTypeId;

                if (!string.IsNullOrEmpty(hedgingFileTypeIds))
                {
                    //获取待转文文档列表
                    var hedgingFileTypeIdList = hedgingFileTypeIds.Split(',').ToList();
                    var caseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
                    var caseHedgingFiles = caseFiles.FindAll(x => x.IsActive && !x.HasHedgingFile && hedgingFileTypeIdList.Contains(x.FileTypeId.ToString()));

                    if (caseHedgingFiles.Any())
                    {
                        caseFile.HedgingFileTypeId = caseFileType.FileTypeId;
                        caseFile.HedgingFileId = new List<long?>();
                        caseHedgingFiles.ForEach(f => caseFile.HedgingFileId.Add(f.FileId));
                    }
                }

                if (!string.IsNullOrEmpty(hedgingFeeTypeIds))
                {
                    //获取待转票通知列表
                    var hedgingFeeTypeIdList = hedgingFeeTypeIds.Split(',').ToList();
                    var caseFees = CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                    var caseHedgingFees = caseFees.FindAll(x => x.IsActived && !x.HasHedgingFile && hedgingFeeTypeIdList.Contains(x.CaseFeeTypeId.ToString()));

                    if (caseHedgingFees.Any())
                    {
                        caseFile.HedgingFileTypeId = caseFileType.FileTypeId;
                        caseFile.HedgingFeeId = new List<long?>();
                        caseHedgingFees.ForEach(f => caseFile.HedgingFeeId.Add(f.CaseFeeId));
                    }
                }

                caseFileList.Add(caseFile);
            }

            var result = false;
            caseFileList.ForEach(caseFile =>
            {
                var c = CaseService.Instance.GetCaseBasic(caseFile.CaseId);
                result = CaseService.Instance.Process(c, caseFile, bytes);
            });

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

        #endregion

        #region 案件自定文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult CaseFileCustomImport(string id)
        {
            return View();
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
         [HttpPost]
        public JsonResult CaseFileCustomImportUploading()
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

            var lstCase = CaseFileService.Instance.ProcessCustomCaseFile(file.FileName, bytes);

            //if (lstCase != null && lstCase.Any())
            //{
            response.Data = lstCase;
            response.Message = "上传成功！";
            response.IsSuccess = true;
            //}
            //else
            //{
            //response.Message = "上传失败！";
            //response.IsSuccess = false;
            //}

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseCustomFileImport(CaseCustomFileUploadModel model)
        {
            var response = new PostResponse();
            try
            {
                bool result = CaseFileService.Instance.CustomFileCaseImportProcess(model.CustomFileCases);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseCustomFileImport", "CaseController.CaseCustomFileImport", ex);
                throw;
            }

            return Json(response);
        }

        #endregion


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult TransmitCaseFile(Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFile.TransmitCaseFileModel model)
        {
            var caseFileType = CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == model.CaseFileTypeId);
            model.CaseFileTypeName = caseFileType != null ? caseFileType.FileTypeName : string.Empty;

            return PartialView("TransmitCaseFile", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult TransmitCaseFeeFile(Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFile.TransmitCaseFileModel model)
        {
            var caseFileType = CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == model.CaseFileTypeId);
            model.CaseFileTypeName = caseFileType != null ? caseFileType.FileTypeName : string.Empty;

            return PartialView("TransmitCaseFeeFile", model);
        }

        [HttpPost]
        public ActionResult TransmitCaseFeeInvoiceFile(Dchien.Legal.Web.Areas.IPR.ViewModels.CaseFile.TransmitCaseFileModel model)
        {
            var caseFileType = CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == model.CaseFileTypeId);
            model.CaseFileTypeName = caseFileType != null ? caseFileType.FileTypeName : string.Empty;

            return PartialView("TransmitCaseFeeInvoiceFile", model);
        }
        

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseIds"></param>
        /// <param name="caseFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Transmit(long customerId, int caseFileTypeId, long[] caseIds,long[] caseFileIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType =
                    CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

                if (caseFileType != null && caseFileType.IsTransformed)
                {
                    CaseFileBaseProcess fileProcess = null;
                    if (caseFileType.CaseTypeId == (int)CaseClassType.Patent)
                    {
                        fileProcess = PatentCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }
                    else
                    {
                        fileProcess = TrademarkCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }

                    fileProcess.CaseIdList = caseIds.ToList();
                    fileProcess.CaseFileIdList = caseFileIds.ToList();

                    //var c = CaseService.Instance.GetCaseBasic(caseIds[0]);

                    //if (c.CaseBasicInfo.CustomerId.HasValue)
                    //{
                    //    customerId = c.CaseBasicInfo.CustomerId.Value;
                    //}

                    var fileName = fileProcess.ExportToWord(customerId, caseFileTypeId);

                    response.Data = customerId + "|" + fileName;
                    response.IsSuccess = true;
                    return Json(response);
                }
                else
                {
                    response.Data = string.Empty;
                    response.IsSuccess = false;
                    response.Message = string.Format("未找到案件文件类型{0}，或该文件类型不是转文文档.", caseFileTypeId);
                    return Json(response);
                }
            }
            catch (NotImplementedException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (ApplicationException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.Transmit", "CaseFileController.Transmit", ex);
                throw;
            }
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseIds"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Inform(long customerId, int caseFileTypeId, long[] caseIds,long[] caseFeeIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType =
                    CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

                if (caseFileType != null && caseFileType.IsTransformed)
                {
                    CaseFileBaseProcess fileProcess = null;
                    if (caseFileType.CaseTypeId == (int)CaseClassType.Patent)
                    {
                        fileProcess = PatentCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }
                    else 
                    {
                        fileProcess = TrademarkCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }

                    fileProcess.CaseFeeIdList = caseFeeIds.ToList();
                    fileProcess.CaseIdList = caseIds.ToList();

                    var fileName = fileProcess.ExportToWord(customerId, caseFileTypeId);

                    response.Data = customerId + "|" + fileName;
                    response.IsSuccess = true;
                    return Json(response);
                }
                else
                {
                    response.Data = string.Empty;
                    response.IsSuccess = false;
                    response.Message = string.Format("未找到案件文件类型{0}，或该文件类型不是转文文档.", caseFileTypeId);
                    return Json(response);
                }
            }
            catch (NotImplementedException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (ApplicationException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.Transmit", "CaseFileController.Transmit", ex);
                throw;
            }
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="customerId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <param name="caseIds"></param>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult TransmitInvoiceFile(long customerId, int caseFileTypeId, long[] caseIds, long[] caseFeeIds)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType =
                    CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

                if (caseFileType != null && caseFileType.IsTransformed)
                {
                    CaseFileBaseProcess fileProcess = null;
                    if (caseFileType.CaseTypeId == (int)CaseClassType.Patent)
                    {
                        fileProcess = PatentCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }
                    else
                    {
                        fileProcess = TrademarkCaseFileProcessFactory.Create((CaseFileType)caseFileTypeId);
                    }

                    fileProcess.CaseFeeIdList = caseFeeIds.ToList();
                    fileProcess.CaseIdList = caseIds.ToList();

                    var fileName = fileProcess.ExportToWord(customerId, caseFileTypeId);

                    response.Data = customerId + "|" + fileName;
                    response.IsSuccess = true;
                    return Json(response);
                }
                else
                {
                    response.Data = string.Empty;
                    response.IsSuccess = false;
                    response.Message = string.Format("未找到案件文件类型{0}，或该文件类型不是转文文档.", caseFileTypeId);
                    return Json(response);
                }
            }
            catch (NotImplementedException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (ApplicationException ex)
            {
                response.Data = string.Empty;
                response.IsSuccess = false;
                response.Message = ex.Message;
                return Json(response);
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.Transmit", "CaseFileController.Transmit", ex);
                throw;
            }
        }
    }
}
