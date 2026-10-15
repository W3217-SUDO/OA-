using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Entity.Infrastructure;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Web.UI.WebControls;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseFileController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseFileController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFileList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseFileListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 10;

            if (caseId > 0)
            {
                caseModel.CaseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
                caseModel.TotalCount = caseModel.CaseFiles.Count;
                caseModel.CaseFiles = caseModel.CaseFiles.Any()
                    ? caseModel.CaseFiles.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<BizCaseFile>();
            }

            return PartialView("CaseFileList", caseModel);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        //[HttpPost]
        //public ActionResult CaseFileList(long caseId, int? pageNo, int? pageSize)
        //{
        //    var caseModel = new CaseFileListModel();
        //    caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
        //    caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 20;

        //    if (caseId > 0)
        //    {
        //        caseModel.CaseFiles = CaseFileService.Instance.GetCaseFiles(caseId);
        //        caseModel.TotalCount = caseModel.CaseFiles.Count;
        //        caseModel.CaseFiles = caseModel.CaseFiles.Any()
        //            ? caseModel.CaseFiles.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
        //                .Take(caseModel.PageSize)
        //                .ToList()
        //            : new List<BizCaseFile>();
        //    }

        //    return PartialView("PartialView/CaseFileList", caseModel);
        //}

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
        [HttpPost]
        public JsonResult CaseFileUploading(CaseFileUploadModel model)
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

            var caseFile = this.ConvertToCaseFile(model, file.FileName, fileSize);
            var canRepeatUpload = CaseFileService.Instance.CheckCaseFileCanRepeatUpload(caseFile);

            if (!canRepeatUpload)
            {
                response.Message = string.Format("案件({0})已存在该类型文档，且不允许重复上传。", caseFile.CaseNo);
                response.IsSuccess = false;
                return Json(response);
            }

            var result = this.ProcessCaseFileUploading(caseFile, bytes);

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
        /// <param name="model"></param>
        /// <param name="fileName"></param>
        /// <param name="fileSize"></param>
        /// <returns></returns>
        private BizCaseFile ConvertToCaseFile(CaseFileUploadModel model, string fileName, long fileSize)
        {
            var caseFile = new BizCaseFile();
            caseFile.CaseId = model.CaseId;
            caseFile.CaseNo = model.CaseNo;
            caseFile.FileTypeId = model.CaseFileTypeId;
            caseFile.FileTypeName = model.CaseFileTypeName;
            caseFile.FileName = fileName;
            caseFile.FileSize = fileSize;
            caseFile.IsActive = true;
            caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;
            caseFile.UploadingTime = model.UploadingTime.HasValue ? model.UploadingTime.Value : DateTime.Now;
            caseFile.HedgingFileTypeId = model.HedgingFileTypeId;
            caseFile.HedgingFileId = model.HedgingFileId;
            caseFile.HedgingFeeId = model.HedgingFeeId;

            caseFile.CaseRequestNo = model.CaseRequestNo;

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
            var c = CaseService.Instance.GetCaseBasic(caseFile.CaseId);
            bool result = CaseService.Instance.Process(c, caseFile, bytes);

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
            var caseFileTypes = CaseTypeService.Instance.GetAllCaseFileTypes();

            model.CaseFileTypeList = caseFileTypes;
            model.UploadingTime = DateTime.Now.Date; // 默认值

            //if (model.HedgingFileTypeId.HasValue && model.HedgingFileTypeId.Value > 0)
            //{
            //    model.CaseFileTypeList =
            //        model.CaseFileTypeList.Where(x => x.FileTypeId == model.HedgingFileTypeId.Value).ToList();
            //}

            return PartialView("CaseFileUpload", model);
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
        public JsonResult CaseFileDelete(long caseFileId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseFileService.Instance.CaseFileDelete(caseFileId);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseFileDelete", "CaseController.CaseFileDelete", ex);
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
    }
}
