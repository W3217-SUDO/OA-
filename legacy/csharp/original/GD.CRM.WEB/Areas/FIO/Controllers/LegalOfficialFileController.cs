using System;
using System.Linq;
using System.Web.Mvc;

using Dchien.Legal.BizModel.FIO;
using Dchien.Legal.Common;
using Dchien.Legal.Web.Areas.FIO.ViewModels;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Case;
using System.IO;
using Dchien.Legal.Service.FIO;
using Dchien.Legal.BizModel.FIO.MetaFile;
using System.Collections.Generic;

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class LegalOfficialFileController : BaseController
    {
        internal Log Logger = new Log("Dchien.Legal.Web.Areas.FIO.Controllers.LegalOfficialFileController");

        #region 文件查询

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult List(string id)
        {
            var model = new LegalOfficialFileModel();
            model.SearchCondition = new Entity.Legal.Case.CaseFileSearchCondition();
            model.SearchCondition.PageId = id;
            model.SearchCondition.UpdateDateFrom = DateTime.Now.Date;
            model.SearchCondition.UpdateDateTo = DateTime.Now.Date;
            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetOfficialFiles(LegalOfficialFileModel model)
        {
            var response = new PostResponse();
            try
            {
                var caseFileList = CaseFileService.Instance.GetCaseFileList(model.SearchCondition);
                var result = new BizLegalOfficialFileResultInfo();
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                result.CaseFileList = caseFileList;
                response.Data = result;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "LegalOfficialFileController.GetFiles", "LegalOfficialFileController.GetFiles", ex);
                response.IsSuccess = false;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult MetaFileList(string id)
        {
            var model = new MetaFileModel();
            model.SearchCondition = new Entity.Legal.Case.MetaFileSearchCondition();
            model.SearchCondition.PageId = id;
            return View("MetaFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetMetaFiles(MetaFileModel model)
        {
            var response = new PostResponse();
            try
            {
                var fileList = OfficalMetaFileService.Instance.GetMetaFileList(model.SearchCondition);
                var result = new BizOfficialMetalFileResultInfo();
                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;
                result.MetaFileList = fileList;
                response.Data = result;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "LegalOfficialFileController.GetMetaFiles", "LegalOfficialFileController.GetMetaFiles", ex);
                response.IsSuccess = false;
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        public ActionResult MetaFile(string id)
        {
            return View("MetaFileUpload");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult MetaFileUpload()
        {
            var response = new PostResponse();
            var files = Request.Files;
            if (files == null || files.Count == 0)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return Json(response);
            }
            var guid = Guid.NewGuid();
            for (var i = 0; i < files.Count; i++)
            {
                int fileLen = files[i].ContentLength;
                Stream stream;
                byte[] bytes = new byte[fileLen];
                stream = files[i].InputStream;
                stream.Read(bytes, 0, fileLen);
                var metaFile = new BizOfficialMetaFile();
                metaFile.FileGuid = Guid.NewGuid().ToString();
                metaFile.CaseNo = "";
                metaFile.FileName = files[i].FileName;
                metaFile.FileExtension = files[i].FileName;
                metaFile.FileSize = files[i].ContentLength;
                metaFile.InformDate = string.IsNullOrEmpty(Request["MetaFile.InformDate"]) ?  DateTime.Now : Convert.ToDateTime(Request["MetaFile.InformDate"]);
                OfficalMetaFileService.Instance.Create(metaFile,bytes);
                response.Data = guid;
                response.IsSuccess = true;
            }
            return new JsonResult()
            {
                Data = response,
                ContentType = "application/json"
            };
        }


        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <param name="metaFileIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Delete(List<string> metaFileIds)
        {
            var response = new PostResponse();
            try
            {
                bool result = OfficalMetaFileService.Instance.Delete(metaFileIds);
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "LegalOfficialFileController.Delete", "LegalOfficialFileController.Delete", ex);
                throw;
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult InformDate()
        {
            return PartialView("InformDate");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult InformDateChange(List<string> metaFileIds, DateTime informDate)
        {
            var response = new PostResponse();
            response.IsSuccess = true;
            try
            {
                metaFileIds.ForEach(fileId =>
                {
                    var metaFile = OfficalMetaFileService.Instance.GetMetaFile(fileId);
                    if (null != metaFile)
                    {
                        metaFile.InformDate = informDate;
                        OfficalMetaFileService.Instance.InformDateChange(metaFile);
                        CaseFileService.Instance.InformDateChange(metaFile.FileGuid, informDate);
                    }
                });
            }
            catch (Exception ex)
            {
                response.Message = "修改失败！";
                response.IsSuccess = false;
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "LegalOfficialFileController.InformDateChange", "LegalOfficialFileController.InformDateChange", ex);
            }
            return Json(response);
        }
    }
}
