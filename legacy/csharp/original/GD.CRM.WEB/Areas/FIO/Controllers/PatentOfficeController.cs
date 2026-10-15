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
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Entity.System;

namespace Dchien.Legal.Web.Areas.FIO.Controllers
{
    [CheckUserLogin]
    public class PatentOfficeController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.PatentOfficeController");

        #region 专利局批量文件导入

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>

        public ActionResult PatentOfficeFileImport(string id)
        {
            var model = new PatentOfficeFileImportModel();

            return View("PatentOfficeFileImport", model);
        }

        /// <summary>
        /// 案件批量导入
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeFileUploading()
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

                var cases = Dchien.Legal.Service.FIO.PatentOffice.PatentOfficeFileService.Instance.ProcessPatentOfficeMetaFile(metaFile, bytes);

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

                Dchien.Legal.Service.FIO.PatentOffice.PatentOfficeFileService.Instance.CreatePatentOfficeFile(officeFiles);

                var caseList = Dchien.Legal.Service.FIO.PatentOffice.PatentOfficeFileService.Instance.GetPatentOfficeFileList(gaIds);

                caseList.ForEach(x =>
                {
                    try
                    {
                        Dchien.Legal.Service.FIO.PatentOffice.PatentOfficeFileService.Instance.PatentOfficeFileImportProcess(x.CaseFileList);
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
                var fileList = PatentOfficeFileService.Instance.GetCasePatentOfficeFileList(fileIds.Keys.ToList());

                fileList.ForEach(x =>
                {
                    if (x.CaseId == 0)
                    {
                        x.CaseId = fileIds[x.FileId];
                    }

                    #region 0.检查案号不匹配

                    if (x.Errors.Any(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001))
                    {
                        if (x.CaseId > 0)
                        {
                            x.Errors.Remove(x.Errors.FirstOrDefault(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001));
                        }
                        else
                        {
                            response.Message += "<br>" + x.Errors.FirstOrDefault(e => e.ErrorCode == ErrorMessage.ErrorCode_10000001).Message;
                            response.IsSuccess = false;
                        }

                    }
                    #endregion

                    #region 1.检查所有费用类型错误

                    if (x.CaseFees != null && x.CaseFees.Any() &&
                        x.Errors.Any(e => e.ErrorCode == ErrorMessage.ErrorCode_10000002))
                    {
                        var caseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();

                        x.CaseFees.ForEach(f =>
                        {
                            if (!caseFeeTypes.Any(t => t.FeeTypeName == f.CaseFeeTypeName))
                            {
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
                    #endregion
                });

                bool result = PatentOfficeFileService.Instance.PatentOfficeFileImportProcess(fileList);

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
                        fileList.FindAll(f => !f.Errors.Any()).Count , 
                        fileList.FindAll(f=>f.Errors.Any()).Count,
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PatentOfficeController.PatentOfficeFileImport","PatentOfficeController.PatentOfficeFileImport", ex);
                response.Message = "导入失败！";
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
        public ActionResult PatentOfficeFileList()
        {
            var model = new CasePatentOfficeFileListModel();

            return View("PatentOfficeFileList", model);
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

                var caseList = PatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

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
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            return View("UnDisposedPatentOfficeFileList", model);
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
                var caseList = PatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(),"PatentOfficeController.UnDisposedPatentOfficeFiles","PatentOfficeController.UnDisposedPatentOfficeFiles", ex);
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
            model.SearchCondition.PageSize = 15;
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

            if (model.SearchCondition.PageId == PageId.PageId_1101002)
            {
                model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
            }
            if (model.SearchCondition.PageId == PageId.PageId_1101006)
            {
                model.SearchCondition.DepartmentId = LoginHelper.GetDepartmentId();
            }

            try
            {
                var caseList = PatentOfficeFileService.Instance.GetPatentOfficeFileList(model.SearchCondition);

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
                 PatentOfficeFileService.Instance.PatentOfficeFileBusinessProcess(officeFileIds.ToList());
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
                PatentOfficeFileService.Instance.PatentOfficeFileBusinessOnProcess(officeFileIds.ToList());
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
                PatentOfficeFileService.Instance.PatentOfficeFileBusinessUnProcess(officeFileIds.ToList());
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
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            return View("PatentOfficeFileAllList", model);
        }


        [HttpPost]
        public JsonResult PatentOfficeFileServiceProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                PatentOfficeFileService.Instance.PatentOfficeFileServiceProcess(officeFileIds.ToList());
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
                PatentOfficeFileService.Instance.PatentOfficeFileServiceOnProcess(officeFileIds.ToList());
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
                PatentOfficeFileService.Instance.PatentOfficeFileServiceUnProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.PatentOfficeFileServiceUnProcess", "PatentOfficeFileController.PatentOfficeFileServiceUnProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 历史官文业务处理

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult HistoryPatentOfficeFileInList(string id)
        {
            var model = new CasePatentOfficeFileListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
            model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();

            return View("HistoryPatentOfficeFileInList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult HistoryCasePatentOfficeFileInList(CasePatentOfficeFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                var caseList = PatentOfficeFileService.Instance.GetHistoryPatentOfficeFileList(model.SearchCondition);

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
        public JsonResult HistoryPatentOfficeFileBusinessProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                PatentOfficeFileService.Instance.HistoryPatentOfficeFileBusinessProcess(officeFileIds.ToList());
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.HistoryPatentOfficeFileBusinessProcess", "PatentOfficeFileController.HistoryPatentOfficeFileBusinessProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        #region 历史官文流程处理

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult HistoryPatentOfficeFileAllList(string id)
        {
            var model = new CasePatentOfficeFileListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;
            model.SearchCondition.PageId = id;
           
            return View("HistoryPatentOfficeFileAllList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult HistoryPatentOfficeFileAllList(CasePatentOfficeFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                var caseList = PatentOfficeFileService.Instance.GetHistoryPatentOfficeFileList(model.SearchCondition);

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



        [HttpPost]
        public JsonResult HistoryPatentOfficeFileServiceProcess(long[] officeFileIds)
        {
            var response = new PostResponse();

            try
            {
                PatentOfficeFileService.Instance.HistoryPatentOfficeFileServiceProcess(officeFileIds.ToList(),"T");
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileController.HistoryPatentOfficeFileServiceProcess", "PatentOfficeFileController.HistoryPatentOfficeFileServiceProcess", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        #endregion

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        public ActionResult PatentOfficeFileCheckList()
        {
            var model = new PatentOfficeFileCheckListModel();
            model.SearchCondition = new CasePatentOfficeFileSearchCondition();
            model.SearchCondition.PageNo = 1;
            model.SearchCondition.PageSize = 15;

            return View("PatentOfficeFileCheckList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CasePatentOfficeFileCheckList(PatentOfficeFileCheckListModel model)
        {
            var response = new PostResponse();

            try
            {
                var list = PatentOfficeFileService.Instance.GetCasePatentOfficeFileCheckList(model.SearchCondition);

                if (list != null && list.Any())
                {
                    var result = new BizPatentOfficeFileCheckListResultInfo();

                    result.TotalItemCount = model.SearchCondition.TotalCount;
                    result.PageNo = model.SearchCondition.PageNo;
                    result.PageSize = model.SearchCondition.PageSize;
                    result.CheckFiles = list;
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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeController.CasePatentOfficeFileCheckList", "PatentOfficeController.CasePatentOfficeFileCheckList", ex);
                response.IsSuccess = false;
            }

            return Json(response);
        }

        public ActionResult PatentOfficeFileCheckListImport()
        {
            var model = new PatentOfficeFileImportModel();
            return PartialView("PatentOfficeFileCheckListImport", model);
        }
        
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [HttpPost]
        public JsonResult PatentOfficeFileCheckListUploading()
        {
            var response = new PostResponse();

            var file = Request.Files[0];

            if (file == null)
            {
                response.Message = "请选择文件进行上传.";
                response.IsSuccess = false;
                return Json(response);
            }

            if (file.FileName.IndexOf(".xlsx") <= 0 && file.FileName.IndexOf(".xls") <= 0)  
            {
                response.Message = "请上传Excel格式文件.";
                response.IsSuccess = false;
                return Json(response);
            }

            int fileLen = file.ContentLength;

            Stream stream;
            byte[] bytes = new byte[fileLen];
            stream = file.InputStream;
            stream.Read(bytes, 0, fileLen);

            try
            {
                var guid = Guid.NewGuid();
                var fileList = PatentOfficeFileService.Instance.ParseCasePatentOfficeFileList(bytes, guid, file.FileName);
                var fileFiterList = fileList.Distinct(new FastPropertyComparer<BizPatentOfficeCheckFile>("FAWENXLH")).ToList();
                var message = "清单共有{0}文件,过滤重复项后正常文件数{1}，已导入{2}文件,未导入{3}文件,遗漏{4}文件.";

                response.Message = string.Format(message,
                                            fileList.Count(),
                                            fileFiterList.Count(),
                                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.Imported).Count(),
                                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.UnImported).Count(),
                                            fileFiterList.FindAll(x => x.PatentOfficeFileStatus == CasePatentOfficeFileStatus.NotExists).Count());

                response.Data = guid;
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "PatentOfficeFileCheckListUploading", "PatentOfficeFileCheckListUploading", ex);
                response.Message = "上传失败！";
                response.IsSuccess = false;
            }

            return new JsonResult()
            {
                Data = response,
                MaxJsonLength = int.MaxValue,
                ContentType = "application/json"
            };
         
         }
    }
}
