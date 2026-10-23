using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using System.Web.UI.WebControls;
using System.Configuration;

using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.BAS.Type;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFile;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.CaseFileProcess;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Entity.Legal.Case;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Service.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseFileController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileList()
        {
              return PartialView("PartialView/CaseFileList");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileTypeId"></param>
        /// <param name="caseNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetCaseFileList(long? fileTypeId, string caseNo, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();
            var _pageNo = pageNo.HasValue ? pageNo.Value : 1;
            var _pageSize = pageSize.HasValue ? pageSize.Value : 10;

            try
            {
                var caseFileList = new List<BizCaseFile>();
                var c =  CaseService.Instance.GetCaseBasic(caseNo);

                if (fileTypeId.HasValue)
                {
                    var caseFileType = Dchien.Legal.Service.Legal.Case.CaseFileTypeService.Instance.GetCaseFileType(fileTypeId.Value);

                    if (caseFileType.TypeId == (int)CaseFileTypeId.FCM)
                    {
                        #region 抓取合同文件

                        var contractFiles = Service.FCM.Contract.File.ContractFileService.Instance.GetContractFileListByContractNo(c.Basic.ContractNo);

                        if (contractFiles != null && contractFiles.Any())
                        {
                            contractFiles.ForEach(f =>
                            {
                                var caseFile = new BizCaseFile();
                                caseFile.CaseId = c.Basic.CaseId;
                                caseFile.CaseNo = c.Basic.CaseNo;
                                caseFile.OnlineUrl = f.OnlineUrl;
                                caseFile.FileId = f.FileId;
                                caseFile.FileName = f.FileName;
                                caseFile.UploadingTime = f.UploadTime;
                                caseFile.UploadingUserName = f.UploadUserName;
                                caseFileList.Add(caseFile);
                            });
                        }

                        #endregion
                    }
                    else if (caseFileType.TypeId == (int)CaseFileTypeId.CRM)
                    {
                        #region 抓取客户文件

                        var customerFiles = Service.CRM.Customer.File.CustomerFileService.Instance.GetCustomerFileListByCustomerNo(c.Basic.CustomerNo);

                        if (customerFiles != null && customerFiles.Any())
                        {
                            customerFiles.ForEach(f =>
                            {
                                var caseFile = new BizCaseFile();
                                caseFile.CaseId = c.Basic.CaseId;
                                caseFile.CaseNo = c.Basic.CaseNo;
                                caseFile.OnlineUrl = f.OnlineUrl;
                                caseFile.FileId = f.FileId;
                                caseFile.FileName = f.FileName;
                                caseFile.UploadingTime = f.UploadTime;
                                caseFile.UploadingUserName = f.UploadUserName;
                                caseFileList.Add(caseFile);
                            });
                        }

                        #endregion 
                    }

                    else if(caseFileType.TypeId == (int)CaseFileTypeId.Investigation || caseFileType.TypeId == (int)CaseFileTypeId.Investigation_Task)
                    {
                        #region 抓调查文件

                        if (!string.IsNullOrEmpty(c.Basic.InvestigationClueNos))
                        {
                            var investigationFiles = InvestigationFileService.Instance.GetInvestigationFileListByClueNo(c.Basic.InvestigationClueNos.Split(',').ToList());

                            if (investigationFiles != null && investigationFiles.Any())
                            {
                                investigationFiles.ForEach(f =>
                                {
                                    var caseFile = new BizCaseFile();
                                    caseFile.CaseId = c.Basic.CaseId;
                                    caseFile.CaseNo = c.Basic.CaseNo;
                                    caseFile.FileId = f.FileId;
                                    caseFile.FileName = f.FileName;
                                    caseFile.OnlineUrl = f.OnlineUrl;
                                    caseFile.UploadingTime = f.UploadingTime;
                                    caseFile.UploadingUserName = f.UploadingUserName;
                                    caseFileList.Add(caseFile);
                                });
                            }
                        }

                        #endregion 
                    }

                    else if (caseFileType.TypeId == (int)CaseFileTypeId.Investigation_Clue)
                    {
                        #region 抓线索文件

                        if (!string.IsNullOrEmpty(c.Basic.InvestigationClueNos))
                        {
                            var caseFiles = InvestigationClueFileService.Instance.GetInvestigationClueFileListByClueNo(c.Basic.InvestigationClueNos.Split(',').ToList());
                            if (caseFiles != null && caseFiles.Any())
                            {
                                caseFiles.ForEach(f =>
                                {
                                    var caseFile = new BizCaseFile();
                                    caseFile.CaseId = c.Basic.CaseId;
                                    caseFile.CaseNo = c.Basic.CaseNo;
                                    caseFile.FileId = f.FileId;
                                    caseFile.FileName = f.FileName;
                                    caseFile.OnlineUrl = f.OnlineUrl;
                                    caseFile.UploadingTime = f.UploadingTime;
                                    caseFile.UploadingUserName = f.UploadingUserName;
                                    caseFileList.Add(caseFile);
                                });
                            }
                        }
                        #endregion 
                    }
                    else if (caseFileType.TypeId == (int)CaseFileTypeId.Investigation_Clue_Evidence)
                    {
                        #region 抓取证文件

                        if (!string.IsNullOrEmpty(c.Basic.InvestigationClueNos))
                        {
                            var caseFiles = InvestigationClueEvidenceFileService.Instance.GetInvestigationClueEvidenceFileListByClueNo(c.Basic.InvestigationClueNos.Split(',').ToList());
                            if (caseFiles != null && caseFiles.Any())
                            {
                                caseFiles.ForEach(f =>
                                {
                                    var caseFile = new BizCaseFile();
                                    caseFile.CaseId = c.Basic.CaseId;
                                    caseFile.CaseNo = c.Basic.CaseNo;
                                    caseFile.FileId = f.FileId;
                                    caseFile.FileName = f.FileName;
                                    caseFile.OnlineUrl = f.OnlineUrl;
                                    caseFile.UploadingTime = f.UploadingTime;
                                    caseFile.UploadingUserName = f.UploadingUserName;
                                    caseFileList.Add(caseFile);
                                });
                            }
                        }

                        #endregion 
                    }
                    else
                    {
                        var caseFiles = CaseFileService.Instance.GetCaseFiles(caseNo);
                        if (caseFiles != null && caseFiles.Any())
                        {
                            caseFiles.ForEach(f =>
                            {
                                if (f.CaseFileTypeId == fileTypeId.Value)
                                {
                                    var caseFile = new BizCaseFile();
                                    caseFile.CaseId = c.Basic.CaseId;
                                    caseFile.CaseNo = c.Basic.CaseNo;
                                    caseFile.FileId = f.FileId;
                                    caseFile.FileName = f.FileName;
                                    caseFile.OnlineUrl = f.OnlineUrl;
                                    caseFile.UploadingTime = f.UploadingTime;
                                    caseFile.UploadingUserName = f.UploadingUserName;
                                    caseFileList.Add(caseFile);
                                }
                            });
                        }
                    }
                }
                else
                {
                    caseFileList = CaseFileService.Instance.GetCaseFiles(caseNo);
                }

                var totalCount = caseFileList.Count;
                caseFileList = caseFileList.Any()
                ? caseFileList.Skip(_pageSize * (_pageNo - 1))
                    .Take(_pageSize)
                    .OrderByDescending(x => x.UploadingTime.Date).ThenByDescending(x => x.FileId)
                    //.OrderByDescending(x => x.FileId)
                    .ToList()
                : new List<BizCaseFile>();

                response.Data = new { CaseFiles = caseFileList , TotalItemCount = totalCount , PageNo = _pageNo, PageSize = _pageSize };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.GetCaseFileList", "CaseFileController.GetCaseFileList", ex);
                throw;
            }

            return Json(response);
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        //[HttpPost]
        //public JsonResult CaseFileUploading(CaseFileUploadModel model)
        //{
        //    var response = this.CheckCaseFileUploading();

        //    if (response != null)
        //    {
        //        return Json(response);
        //    }

        //    response = new PostResponse();

        //    for (int i = 0; i < Request.Files.Count; i++)
        //    {
        //        var file = Request.Files[i];
        //        int fileSize = file.ContentLength;
        //        var bytes = new byte[fileSize];
        //        using (var stream = file.InputStream)
        //        {
        //            stream.Read(bytes, 0, fileSize);
        //        }
        //        //var caseFile = this.ConvertToCaseFile(model, file.FileName, fileSize);
        //        //var result = this.ProcessCaseFileUploading(caseFile, bytes);
        //    }   
           
        //    response.Message = "上传成功！";
        //    response.IsSuccess = true;
           
        //    return Json(response);
        //}

        [HttpPost]
        public JsonResult CaseFileRename(long caseFileId, string caseFileName)
        {
            var response = new  PostResponse();

            if (Path.GetFileNameWithoutExtension(caseFileName) == string.Empty)
            {
                response.Message = "文件名为空，不允许修改！";
                response.IsSuccess = false;
                return Json(response);
            }
            var result = CaseFileService.Instance.CaseFileRename(caseFileId, caseFileName);

            if (result)
            {
                response.Message = "修改成功！";
                response.IsSuccess = true;
                return Json(response);
            }

            response.Message = "修改失败！";
            response.IsSuccess = false;

            return Json(response);
        }

        //[HttpPost]
        //public JsonResult CaseFileWebUpload(CaseFileUploadModel model)
        //{
        //    var response = this.CheckCaseFileUploading();

        //    if (response != null)
        //    {
        //        return Json(response);
        //    }

        //    response = new PostResponse();

        //    for (int i = 0; i < Request.Files.Count; i++)
        //    {
        //        var file = Request.Files[i];
        //        int fileSize = file.ContentLength;
        //        var bytes = new byte[fileSize];
        //        using (var stream = file.InputStream)
        //        {
        //            stream.Read(bytes, 0, fileSize);
        //        }

        //        var fileTypes = Dchien.Legal.Service.Legal.Case.CaseFileTypeService.Instance.GetCaseFileTypes(model.CaseNo);
        //        var floders = new List<string>();

        //        if (!string.IsNullOrEmpty(model.Relativepath) && model.Relativepath.StartsWith("/"))
        //        {
        //            floders = model.Relativepath.Substring(1, model.Relativepath.LastIndexOf("/")-1).Split('/').ToList();
        //        }

        //        var caseFile = this.ConvertToCaseFile(model.CaseId, file.FileName, fileSize);


        //        if (floders.Any())
        //        {
        //            var fileType = Dchien.Legal.Service.Legal.Case.CaseFileTypeService.Instance.GetCaseFileType(model.CaseFileTypeId.Value, fileTypes, floders);

        //            model.CaseFileTypeId = fileType.FileTypeId;
        //        }
        //        else
        //        {
        //            model.CaseFileTypeId = model.CaseFileTypeId.Value;
        //        }

 
        //        caseFile.CaseFileTypeId = model.CaseFileTypeId.Value;

        //        var result = this.ProcessCaseFileUploading(caseFile, bytes);
        //    }

        //    response.Message = "上传成功！";
        //    response.IsSuccess = true;

        //    return Json(response);
        //}


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult MultiCaseFileWebUpload(MultiCaseFileUploadModel model)
        {
            var response = this.CheckCaseFileUploading();

            if (response != null)
            {
                return Json(response);
            }

            response = new PostResponse();

            model.CaseNos.Split(',').ToList().ForEach(caseNo =>
            {
                var c = CaseService.Instance.GetCaseBasic(caseNo);

                for (int i = 0; i < Request.Files.Count; i++)
                {
                    var file = Request.Files[i];
                    int fileSize = file.ContentLength;
                    var bytes = new byte[fileSize];
                    using (var stream = file.InputStream)
                    {
                        stream.Read(bytes, 0, fileSize);
                    }

                    var fileTypes = Dchien.Legal.Service.Legal.Case.CaseFileTypeService.Instance.GetCaseFileTypes(caseNo);
                    var floders = new List<string>();

                    if (!string.IsNullOrEmpty(model.Relativepath) && model.Relativepath.StartsWith("/"))
                    {
                        floders = model.Relativepath.Substring(1, model.Relativepath.LastIndexOf("/") - 1).Split('/').ToList();
                    }

                    if (floders.Any())
                    {
                        var fileType = Dchien.Legal.Service.Legal.Case.CaseFileTypeService.Instance.GetCaseFileType(model.CaseFileTypeId.Value, fileTypes, floders);

                        model.CaseFileTypeId = fileType.FileTypeId;
                    }
                    else
                    {
                        model.CaseFileTypeId = model.CaseFileTypeId.Value;
                    }

                    var caseFile = this.ConvertToCaseFile(c.Basic.CaseId, c.Basic.CaseNo, model.CaseFileTypeId.Value, file.FileName, fileSize);

                    var result = this.ProcessCaseFileUploading(caseFile, bytes);
                }
            } );
           
            response.Message = "上传成功！";
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <param name="fileName"></param>
        /// <param name="fileSize"></param>
        /// <returns></returns>
        private BizCaseFile ConvertToCaseFile(long caseId,string caseNo,long caseFileTypeId, string fileName, long fileSize)
        {
            var caseFile = new BizCaseFile();
            caseFile.CaseId = caseId;
            caseFile.CaseNo = caseNo;
            caseFile.CaseFileTypeId = caseFileTypeId;
            caseFile.FileTypeId = (int)CaseFileType.FileType_Unknow;
            caseFile.FileTypeName =  CaseFileType.FileType_Unknow.ToString();
            caseFile.FileName = fileName;
            caseFile.FileSize = fileSize;
            caseFile.IsActive = true;
            caseFile.UploadingTime = DateTime.Now;
            caseFile.UploadingTime =  DateTime.Now;
            caseFile.UploadingUser = LoginHelper.GetUserName();

            return caseFile;
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFile"></param>
        /// <param name="bytes"></param>
        /// <returns></returns>
        private bool ProcessCaseFileUploading(BizCaseFile caseFile, byte[] bytes)
        {
            bool result = CaseFileService.Instance.Create(caseFile, bytes);

            return result;
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
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileUpload(CaseFileUploadModel model)
        {
            if (model == null)
            {
                throw new ArgumentNullException("model");
            }
 
            model.UploadingTime = DateTime.Now.Date; // 默认值

            return PartialView("PartialView/CaseFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileUnlock(long caseFileId)
        {
            var response = new PostResponse();

            bool result = CaseFileService.Instance.CaseFileUnlock(caseFileId);

            if (result)
            {
                response.Message = "解锁成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "解锁失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileDelete(List<long> caseFileIds)
        {
            var response = new PostResponse();

            try
            {
                caseFileIds.ForEach(caseFileId => 
                {
                    CaseFileService.Instance.CaseFileDelete(caseFileId);
                });

                response.Message = "删除成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.CaseFileDelete", "CaseFileController.CaseFileDelete", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="caseFileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetHedgingFileAndFeeList(long caseId, int caseFileTypeId)
        {
            var response = new PostResponse();

            //var caseFileType =
            //    CaseTypeService.Instance.GetAllCaseFileTypes().FirstOrDefault(x => x.FileTypeId == caseFileTypeId);

            //if (caseFileType == null)
            //{
            //    response.Message = "文件类型未找到.";
            //    response.IsSuccess = false;
            //    return Json(response); 
            //}

            //var hedgingFileTypeIds = caseFileType.HedgingFileTypeId;
            //var hedgingFeeTypeIds = caseFileType.HedgingFeeTypeId;

            //var caseHedgingFiles = new List<BizCaseFile>();
            //var caseHedgingFees = new List<BizCaseFeeItem>();

            //if (!string.IsNullOrEmpty(hedgingFileTypeIds))
            //{
            //    //获取待转文文档列表
            //    var hedgingFileTypeIdList = hedgingFileTypeIds.Split(',').ToList();
            //    var caseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
            //    caseHedgingFiles = caseFiles.FindAll(x => x.IsActive && !x.HasHedgingFile && hedgingFileTypeIdList.Contains(x.FileTypeId.ToString()));
            //}

            //if (!string.IsNullOrEmpty(hedgingFeeTypeIds))
            //{
            //    //获取待转票通知列表
            //    var hedgingFeeTypeIdList = hedgingFeeTypeIds.Split(',').ToList();
            //    var caseFees = CaseFeeService.Instance.GetCaseFeeItems(caseId);
            //    caseHedgingFees = caseFees.FindAll(x => x.IsActive && !x.HasHedgingFile && hedgingFeeTypeIdList.Contains(x.FeeTypeId.ToString()));
            //}

            // response.Data = new Tuple<List<BizCaseFile>, List<BizCaseFeeItem>>(caseHedgingFiles,caseHedgingFees);

            response.IsSuccess = true;

            //对冲文件
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult FileType()
        {
            return PartialView("PartialView/FileType");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileTypeChange(List<long> caseFileIds,long fileTypeId)
        {
            var response = new PostResponse();

            try
            {
                CaseFileService.Instance.CaseFileTypeChange(caseFileIds, fileTypeId);

                response.Message = "变更成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.CaseFileTypeChange", "CaseFileController.CaseFileTypeChange", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult AuthorizationLetterCreate(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                var fileProcess = CaseLetterBaseProcessFactory.Create(CaseFileType.FileType_110020);
                var fileName = fileProcess.ExportToWord(caseNos);
                response.Data = new { FileName = fileName };
                response.Message = "生成成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.AuthorizationLetterCreate", "REDACTED_ARCHIVE_ONLY", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult LawyersLetterCreate(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                var fileProcess = CaseLetterBaseProcessFactory.Create(CaseFileType.FileType_110021);
                var fileName = fileProcess.ExportToWord(caseNos);
                response.Data = new { FileName = fileName };
                response.Message = "生成成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.LawyersLetterCreate", "CaseFileController.LawyersLetterCreate", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult IdentificationLetterCreate(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                var fileProcess = CaseLetterBaseProcessFactory.Create(CaseFileType.FileType_110022);
                var fileName = fileProcess.ExportToWord(caseNos);
                response.Data = new { FileName = fileName };
                response.Message = "生成成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.IdentificationLetter", "CaseFileController.IdentificationLetter", ex);
                throw;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult SettlementListCreate(List<string> caseNos)
        {
            var response = new PostResponse();

            try
            {
                var fileProcess = CaseLetterBaseProcessFactory.Create(CaseFileType.FileType_110050);
                var fileName = fileProcess.ExportSettlementManifest(caseNos);
                response.Data = new { FileName = fileName };
                response.Message = "生成成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.SettlementListCreate", "CaseFileController.SettlementListCreate", ex);
                throw;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult MultiCaseFileUpload(string caseNos,long? caseFileTypeId)
        {
            var model = new MultiCaseFileUploadModel();
            model.CaseNos = caseNos;
            model.CaseFileTypeId = caseFileTypeId;
            model.UploadingTime = DateTime.Now;
            return PartialView("PartialView/MultiCaseFileUpload", model);
        }

        /// <summary>
        /// 
        /// </summary>
        public JsonResult WordSave(long caseFileId)
        {
            var response = new PostResponse();
            var caseFile = CaseFileService.Instance.GetCaseFile(caseFileId);

            if (caseFile != null)
            {
                try
                {
                    response.Message = "修改成功！";
                    response.IsSuccess = true;
                    ViewBag.Message = "修改成功.";
                    var caseFilePath = Path.Combine(FileHelper.CaseFiles, caseFile.CaseNo, caseFile.FileName);
                    PageOffice.FileSaver fs = new PageOffice.FileSaver();
                    fs.SaveToFile(caseFilePath);
                    fs.Close();
                }
                catch (Exception ex)
                {
                    response.Message = "修改失败！";
                    ViewBag.Message = ex.Message;

                    Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileController.WordSave", "CaseFileController.WordSave", ex);

                }
            }

            return Json(response); 

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>

        public ActionResult CaseFileWordEdit(long caseFileId)
        {
            var caseFile = CaseFileService.Instance.GetCaseFile(caseFileId);

            if (caseFile != null)
            {
                PageOffice.PageOfficeCtrl pc = new PageOffice.PageOfficeCtrl();
                pc.AddCustomToolButton("保存", "Save()", 1);

                pc.SaveFilePage = ConfigurationManager.AppSettings["onlineurl"] + "/CaseFile/WordSave?CaseFileId=" + caseFileId;
                pc.ServerPage = ConfigurationManager.AppSettings["onlineurl"] + "/pageoffice/server.aspx";
                var caseFilePath = Path.Combine(FileHelper.CaseFiles,caseFile.CaseNo,caseFile.FileName);

                pc.AddCustomToolButton("隐藏痕迹", "hideRevision()", 18);
                pc.AddCustomToolButton("显示痕迹", "showRevision()", 9);

                // **关键代码 禁止拷贝文档内容到外部 **
                //pc.DisableCopyOnly = true;

                pc.WebOpen(caseFilePath, FileHelper.GetPageOfficeOpenModeType(caseFile.FileName), LoginHelper.GetUserChName());

                ViewBag.EditorHtml = pc.GetHtmlCode("PageOfficeCtrl1");
            }
            return View();
        }
    }
 }
