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

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class PCTPatentOfficeController : BaseController
    {
        internal Log Logger = new Log("FIO.Controllers.PCTPatentOfficeController");

        #region 专利局批量文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>

        public ActionResult PCTPatentOfficeFileImport(string id)
        {
            var model = new PCTPatentOfficeFileImportModel();

            return View("PCTPatentOfficeFileImport", model);
        }

        /// <summary>
        /// 案件批量导入
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PCTPatentOfficeFileUploading()
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
                OfficeMetaFileService.Instance.Create(metaFile, bytes);

                var cases = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.ProcessPatentOfficeMetaFile(metaFile, bytes);

                var gaIds = new List<string>();
                var officeFiles = new List<BizPatentOfficeFile>();
                cases.ForEach(x =>
                {
                    if (x.CaseFileList != null && x.CaseFileList.Any())
                    {
                        officeFiles.AddRange(x.CaseFileList);

                        x.CaseFileList.ForEach(f =>
                        {
                            if (!gaIds.Any(gaId => gaId == f.TONGZHISID))
                            {
                                gaIds.Add(f.TONGZHISID);
                            }
                        });
                    }
                });

                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.CreatePatentOfficeFile(officeFiles);

                var caseList = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.GetPatentOfficeFileList(gaIds);

                caseList.ForEach(x =>
                {
                    try
                    {
                        Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileImportProcess(x.CaseFileList);
                    }
                    catch (Exception ex)
                    {
                        Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileUploading", "PatentOfficeFileImportProcess", ex);
                    }
                });

                if (caseList.Any())
                {
                    response.Data = new BizCaseOfficePrimaryFileResultInfo()
                    {
                        Cases = caseList,
                    };

                    response.Message = "上传成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "上传失败！";
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PatentOfficeFileUploading","PatentOfficeFileUploading", ex);
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

        /// <summary>
        /// 
        /// </summary>
        /// <param name="selectedIds"></param>
        /// <returns></returns>

        [HttpPost]
        public JsonResult PatentOfficeFileImport(List<string> selectedIds)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            //文件Id，案件Id
            var fileIds = new Dictionary<long, long>();

            if (selectedIds == null || !selectedIds.Any())
            {
                response.Message = "请选择需要导入的文件！";
                response.IsSuccess = false;
                return Json(response);
            }

            selectedIds.ForEach(x =>
            {
                var fileId = long.Parse(x.Split(',')[0]);
                var caseId = long.Parse(x.Split(',')[1]);

                if (!fileIds.ContainsKey(fileId))
                {
                    fileIds.Add(fileId, caseId);
                }
            });

            try
            {
                var fileList = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.GetCasePatentOfficeFileList(fileIds.Keys.ToList());

                fileList.ForEach(x =>
                {
                    //if (x.CaseId == 0)
                    //{
                    x.CaseId = fileIds[x.FileId];
                    //}

                    #region 0.检查案号不匹配

                    var case_errors = new StringBuilder();

                    if (x.Errors.Any(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001))
                    {
                        if (x.CaseId > 0)
                        {
                            x.Errors.Remove(x.Errors.FirstOrDefault(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001));
                        }
                        else
                        {
                            case_errors.Append("<br>" + x.Errors.FirstOrDefault(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001).Message);
                            response.Message += "<br>" + x.Errors.FirstOrDefault(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001).Message;
                            response.IsSuccess = false;
                        }

                    }
                    #endregion

                    #region 1.检查所有费用类型错误

                    var casefee_errors = new StringBuilder();

                    if (x.CaseFees != null && x.CaseFees.Any() &&
                        x.Errors.Any(e => e.ErrorCode == ErrorMessage.ErrorCode_10000002))
                    {
                        var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

                        x.CaseFees.ForEach(f =>
                        {
                            if (!caseFeeTypes.Any(t => t.FeeTypeName == f.CaseFeeTypeName))
                            {
                                casefee_errors.Append(string.Format("<br>{0}未匹配,请联系管理员增加."));
                                response.Message += string.Format("<br>{0}未匹配,请联系管理员增加.",
                                    f.CaseFeeTypeName);
                                response.IsSuccess = false;
                            }

                        });
                    }



                    #endregion

                    #region 2.检查所有专利局目录标识错误

                    if (x.Errors.Any(e => e.ErrorCode == ErrorMessage.ErrorCode_10000003))
                    {
                        //var caseFileTypes = CaseTypeService.Instance.GetAllCaseFileTypes();
                    }


                    if (string.IsNullOrEmpty(case_errors.ToString()) && string.IsNullOrEmpty(casefee_errors.ToString()))
                    {
                        x.Errors.Clear();
                    }

                    #endregion
                });

                bool result = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileImportProcess(fileList);

                if (!result)
                {
                    var sb = new StringBuilder();
                    fileList.ForEach(x =>
                    {
                        x.Errors.ForEach(error =>
                        {
                            sb.Append(error.Message + "<br>");
                        });
                    });
                    response.IsSuccess = false;
                    response.Message = sb.ToString();
                }
                else
                {
                    var sb = new StringBuilder();
                    fileList.ForEach(x =>
                    {
                        x.Errors.ForEach(error =>
                        {
                            sb.Append(error.Message + "<br>");
                        });
                    });

                    response.IsSuccess = true;
                    response.Message = string.Format("本次共导入{0}个文件,存在错误{1}个文件.<br/>{2}",
                        fileList.FindAll(f => !f.Errors.Any()).Count,
                        fileList.FindAll(f => f.Errors.Any()).Count,
                        sb.ToString());
                    response.Data = fileList.FindAll(f => !f.Errors.Any()).Select(x => x.FileId.ToString()).ToArray();
                }

            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.PatentOfficeFileImport", "PatentOfficeController.PatentOfficeFileImport", ex);
                response.Message = "导入失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="selectedIds"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeFileDelete(List<string> selectedIds)
        {
            var response = new PostResponse();
            response.IsSuccess = true;

            //文件Id，案件Id
            var fileIds = new Dictionary<long, long>();

            if (selectedIds == null || !selectedIds.Any())
            {
                response.Message = "请选择需要导入的文件！";
                response.IsSuccess = false;
                return Json(response);
            }

            selectedIds.ForEach(x =>
            {
                var fileId = long.Parse(x.Split(',')[0]);
                var caseId = long.Parse(x.Split(',')[1]);

                if (!fileIds.ContainsKey(fileId))
                {
                    fileIds.Add(fileId, caseId);
                }
            });

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.DeleteCasePatentOfficeFile(fileIds.Keys.ToList());
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.PatentOfficeFileDelete", "PatentOfficeController.PatentOfficeFileDelete", ex);
                response.Message = "删除失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 专利局文件查询

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult PCTPatentOfficeFileList()
        {
            var model = new CasePatentOfficeFileListModel();

            return View("PCTPatentOfficeFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public JsonResult CasePatentOfficeFiles(CasePatentOfficeFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                model.SearchCondition.Status = CasePatentOfficeFileStatus.Imported;
                model.SearchCondition.FileType = "PCT";

                var caseList = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

                if (caseList != null && caseList.Any())
                {
                    var result = new BizPatentOfficeFileResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.Cases = caseList;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.CasePatentOfficeFiles", "PatentOfficeController.CasePatentOfficeFiles", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 未导入专利官文

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult UnDisposedPatentOfficeFileList(string id)
        {
            var model = new CasePatentOfficeFileListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.PageId = id;
            return View("UnDisposedPCTPatentOfficeFileList", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult UnDisposedPatentOfficeFiles(CasePatentOfficeFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                model.SearchCondition.Status = CasePatentOfficeFileStatus.UnImported;
                model.SearchCondition.FileType = "PCT";
                var caseList = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

                if (caseList != null && caseList.Any())
                {
                    var result = new BizPatentOfficeFileResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.Cases = caseList;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.UnDisposedPatentOfficeFiles", "PatentOfficeController.UnDisposedPatentOfficeFiles", ex);
                response.IsSuccess = false;
            }

            return Json(response);

        }

        #endregion

        #region 专利官文业务处理

        public ActionResult PatentOfficeFileInList(string id)
        {
            var model = new CasePatentOfficeFileListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.PageId = id;

            //model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

            return View("PatentOfficeFileInList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CasePatentOfficeFileInList(CasePatentOfficeFileListModel model)
        {
            var response = new PostResponse();

            model.SearchCondition.Status = CasePatentOfficeFileStatus.Imported;
            model.SearchCondition.FileType = "PCT";

            if (model.SearchCondition.PageId == PageId.PageId_1101006004)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            else if (model.SearchCondition.PageId == PageId.PageId_1101006008)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }

            try
            {
                var caseList = Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.GetPatentOfficeFileInList(model.SearchCondition);

                if (caseList != null && caseList.Any())
                {
                    var result = new BizPatentOfficeFileResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.Cases = caseList;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.CasePatentOfficeFileInList", "PatentOfficeController.CasePatentOfficeFileInList", ex);
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
        public JsonResult PatentOfficeFileBusinessProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileBusinessProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileBusinessProcess", "PatentOfficeFileController.PatentOfficeFileBusinessProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        public JsonResult PatentOfficeFileBusinessOnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileBusinessOnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileBusinessOnProcess", "PatentOfficeFileController.PatentOfficeFileBusinessOnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        [HttpPost]
        public JsonResult PatentOfficeFileBusinessUnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileBusinessUnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileBusinessUnProcess", "PatentOfficeFileController.PatentOfficeFileBusinessUnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 专利官文流程处理

        public ActionResult PatentOfficeFileAllList(string id)
        {
            var model = new CasePatentOfficeFileListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 20;
            model.SearchCondition.PageId = id;
            return View("PatentOfficeFileAllList", model);
        }


        [HttpPost]
        public JsonResult PatentOfficeFileServiceProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileServiceProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileServiceProcess", "PatentOfficeFileController.PatentOfficeFileServiceProcess", ex);
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
        public JsonResult PatentOfficeFileServiceOnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileServiceOnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileServiceOnProcess", "PatentOfficeFileController.PatentOfficeFileServiceOnProcess", ex);
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
        public JsonResult PatentOfficeFileServiceUnProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                Dchien.Legal.Service.FIO.PCTPatentOffice.PCTPatentOfficeFileService.Instance.PatentOfficeFileServiceUnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileServiceUnProcess", "PatentOfficeFileController.PatentOfficeFileServiceUnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

    }
}
