using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using System.Web.Mvc;
using System.Web.UI.WebControls;

using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Areas.Legal.ViewModels.CaseFile;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.CaseFileProcess;
using Dchien.Legal.Entity.Legal.Case;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseFileTypeController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseFileTypeController");
    
        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileTypeId"></param>
        /// <param name="parentFileTypeId"></param>
        /// <param name="caseNo"></param>
        /// <param name="fileTypeName"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileTypeCreate(long? fileTypeId, long parentFileTypeId, string caseNo, string fileTypeName)
        {
            var response = new PostResponse();
 
            try
            {
                var caseFileType = new BizCaseFileType();
                caseFileType.ParentFileTypeId = parentFileTypeId;
                caseFileType.CaseNo = caseNo;
                caseFileType.FileTypeName = fileTypeName;
                caseFileType.TypeId = (int)CaseFileTypeId.Case_Customize;
                CaseFileTypeService.Instance.Create(caseFileType);
                response.Data = new { CaseFileType = caseFileType };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.CaseFileTypeCreate", "CaseFileTypeController.CaseFileTypeCreate", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileTypeId"></param>
        /// <param name="fileTypeName"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileTypeRename(long fileTypeId, string fileTypeName)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType = new BizCaseFileType();
                caseFileType.FileTypeId = fileTypeId;
                caseFileType.FileTypeName = fileTypeName;
                CaseFileTypeService.Instance.Rename(caseFileType);
                response.Data = new { CaseFileType = caseFileType };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.CaseFileTypeRename", "CaseFileTypeController.CaseFileTypeRename", ex);
                throw;
            }

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileTypeRemove(long fileTypeId)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType = new BizCaseFileType();
                caseFileType.FileTypeId = fileTypeId;
                CaseFileTypeService.Instance.Delete(caseFileType);
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.CaseFileTypeRemove", "CaseFileTypeController.CaseFileTypeRemove", ex);
                throw;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseFileTypeRemoveCheck(long fileTypeId)
        {
            var response = new PostResponse();

            try
            {
                var caseFileType = new BizCaseFileType();
                caseFileType.FileTypeId = fileTypeId;
                var canRemove = CaseFileTypeService.Instance.CanRemove(caseFileType);
                response.Data = new { CanRemove = canRemove };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.CaseFileTypeRemoveCheck", "CaseFileTypeController.CaseFileTypeRemoveCheck", ex);
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
        public JsonResult GetCaseFileTypeList(string caseNo)
        {
            var response = new PostResponse();

            try
            {
                var caseFileTypes = CaseFileTypeService.Instance.GetCaseFileTypes(caseNo);
                response.Data = new { CaseFileTypes = caseFileTypes };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.GetCaseFileTypeList", "CaseFileTypeController.GetCaseFileTypeList", ex);
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
        public JsonResult GetCaseFileTypeListForChange(string caseNo)
        {
            var response = new PostResponse();

            try
            {
                caseNo = string.IsNullOrEmpty(caseNo) ? "SH15000001" : caseNo;

                var caseFileTypes = CaseFileTypeService.Instance.GetCaseFileTypes(caseNo);
                
                response.Data = new {
                    CaseFileTypes = caseFileTypes.FindAll(x=>
                    x.TypeId == (int)CaseFileTypeId.Case_7
                    || x.TypeId == (int)CaseFileTypeId.Case_8
                    || x.TypeId == (int)CaseFileTypeId.Case_9
                    || x.TypeId == (int)CaseFileTypeId.Case_10
                    || x.TypeId == (int)CaseFileTypeId.Case_11
                    || x.TypeId == (int)CaseFileTypeId.Case_12
                    || x.TypeId == (int)CaseFileTypeId.Case_Customize)
                };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseFileTypeController.GetCaseFileTypeListForChange", "CaseFileTypeController.GetCaseFileTypeListForChange", ex);
                throw;
            }

            return Json(response);
        }





    }
}
