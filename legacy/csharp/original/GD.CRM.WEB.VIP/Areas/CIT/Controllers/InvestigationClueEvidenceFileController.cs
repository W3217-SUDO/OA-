using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Text;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.BizModel.Legal.Investigation.Evidence;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Entity.Account.Message;
using Dchien.Legal.DataAccess.System;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue.Evidence.File;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationClueEvidenceFileController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueEvidenceFileController");

        [CheckUserLogin]
        public ActionResult InvestigationClueEvidenceFileIn()
        {
            return View("InvestigationClueEvidenceFileIn");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationClueEvidenceInvoiceFileIn()
        {
            return View("InvestigationClueEvidenceInvoiceFileIn");
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueEvidenceFileInUpload()
        {
            var response = this.CheckFileUploading();

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

            var lst = InvestigationClueEvidenceFileService.Instance.ProcessInvestigationClueEvidenceFileIn(file.FileName, bytes);

            if (lst != null && lst.Any())
            {
                var list = new List<BizInvestigationClue>();

                lst.ForEach(f =>
                {
                    var investigationClueEvidence = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidenceByNotarialNo(Path.GetFileNameWithoutExtension(f));

                    if (investigationClueEvidence != null)
                    {
                        investigationClueEvidence.Basic.FileName = f;
                        var investigationClue = InvestigationClueService.Instance.GetInvestigationClueBasicByGuid(investigationClueEvidence.Basic.ClueGuid);
                        var investigation = InvestigationService.Instance.GetInvestigation(investigationClue.Basic.InvestigationNo);
                        investigationClue.Investigation = investigation;
                        investigationClue.InvestigationClueEvidenceList = new List<BizInvestigationClueEvidence>();
                        investigationClue.InvestigationClueEvidenceList.Add(investigationClueEvidence);

                        list.Add(investigationClue);
                    }
                });

                response.Data = new { InvestigationClues = list, PrimaryFileName = file.FileName};
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
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueEvidenceInvoiceFileInUpload()
        {
            var response = this.CheckFileUploading();

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

            var lst = InvestigationClueEvidenceFileService.Instance.ProcessInvestigationClueEvidenceFileIn(file.FileName, bytes);

            if (lst != null && lst.Any())
            {
                var list = new List<BizInvestigationClue>();

                lst.ForEach(f =>
                {
                    var investigationClueEvidence = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidenceByInvoiceNo(Path.GetFileNameWithoutExtension(f));

                    if (investigationClueEvidence != null)
                    {
                        investigationClueEvidence.Basic.FileName = f;
                        var investigationClue = InvestigationClueService.Instance.GetInvestigationClueBasicByGuid(investigationClueEvidence.Basic.ClueGuid);
                        var investigation = InvestigationService.Instance.GetInvestigation(investigationClue.Basic.InvestigationNo);
                        investigationClue.Investigation = investigation;
                        investigationClue.InvestigationClueEvidenceList = new List<BizInvestigationClueEvidence>();
                        investigationClue.InvestigationClueEvidenceList.Add(investigationClueEvidence);

                        list.Add(investigationClue);
                    }
                });

                response.Data = new { InvestigationClues = list, PrimaryFileName = file.FileName };
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
        /// <param name="evidenceFiles"></param>
        /// <param name="primaryFileName"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueEvidenceFileImport(List<BizInvestigationClueEvidenceFile> evidenceFiles, string primaryFileName)
        {
            var response = new PostResponse();

            bool result = true;

            evidenceFiles.ToList().ForEach(x =>
            {
                var fileName = x.FileName;
               
                var investigationClueEvidence = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidence(x.EvidenceGuid);
                var investigationClue = InvestigationClueService.Instance.GetInvestigationClueBasicByGuid(investigationClueEvidence.Basic.ClueGuid);

                x.EvidenceGuid = investigationClueEvidence.Basic.EvidenceGuid;
                x.ClueGuid = investigationClueEvidence.Basic.ClueGuid;
                x.UploadingTime = DateTime.Now;
                x.UploadingUser = LoginHelper.GetUserName();
                x.FileTypeId = (int)FileType.FileType_10000003;

                byte[] bytes = null;

                if (Path.GetExtension(primaryFileName) != null && Path.GetExtension(primaryFileName).ToLower() == ".zip")
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(primaryFileName), x.FileName));
                }
                else
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.FileName));
                }

                var c = CaseService.Instance.GetCaseBasicByClueNo(investigationClue.Basic.ClueNo);

                if (c != null)
                {
                    //如果案件状态是等待公证书,变更成新案待分配
                    if (c.Basic.CasePhaseId == (int)CasePhaseType.Phase_101001)
                    {
                        c.Basic.CasePhaseId = (int)CasePhaseType.Phase_101002;
                        var caseNos = new List<string>();
                        caseNos.Add(c.Basic.CaseNo);
                        CaseService.Instance.UpdateMultipleCase(caseNos, null, null, null, null, (int)CasePhaseType.Phase_101002, null);

                        #region 已生成案件-审核公证书消息

                        var message = MessageService.Instance.NewMessage("审核公证书",
                            string.Format("案号{0},收到一份新的公证书,文件名：{1},请尽快审核并更改案件阶段至新案待分配.", c.Basic.CaseNo, fileName),
                            investigationClue.Basic.BusinessOwner,
                            MessageType.System_Sms_1,
                            true);

                        MessageService.Instance.CreateUpdate(message);

                        #endregion

                    }
                    else if (!string.IsNullOrEmpty(c.Basic.CaseAssistant))
                    {
                        #region 提醒律师助理有新公证书

                        foreach (var caseAssistant in c.Basic.CaseAssistant.Split(','))
                        {
                            var message = MessageService.Instance.NewMessage("新收公证书",
                                     string.Format("案号{0},收到一份新的公证书，文件名：{1}", c.Basic.CaseNo, fileName),
                                    caseAssistant,
                                    MessageType.System_Sms_1,
                                    true);

                            MessageService.Instance.CreateUpdate(message);
                        }

                        #endregion
                    }
                }
                else
                {
                    #region 未生成案件-审核公证书消息

                    var message = MessageService.Instance.NewMessage("审核公证书",
                        string.Format("线索号{0},收到一份新的公证书,文件名：{1},请尽快审核,生成案件更改案件阶段至新案待分配.", investigationClue.Basic.ClueNo, fileName),
                        investigationClue.Basic.BusinessOwner,
                        MessageType.System_Sms_1,
                        true);

                    MessageService.Instance.CreateUpdate(message);

                    #endregion
                }

                result = InvestigationClueEvidenceFileService.Instance.CreateUpdate(x, bytes);
            });

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

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="evidenceFiles"></param>
        /// <param name="primaryFileName"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueEvidenceInvoiceFileImport(List<BizInvestigationClueEvidenceFile> evidenceFiles, string primaryFileName)
        {
            var response = new PostResponse();

            bool result = true;

            evidenceFiles.ToList().ForEach(x =>
            {
                var fileName = x.FileName;

                var investigationClueEvidence = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidence(x.EvidenceGuid);
                var investigationClue = InvestigationClueService.Instance.GetInvestigationClueBasicByGuid(investigationClueEvidence.Basic.ClueGuid);

                x.EvidenceGuid = investigationClueEvidence.Basic.EvidenceGuid;
                x.ClueGuid = investigationClueEvidence.Basic.ClueGuid;
                x.UploadingTime = DateTime.Now;
                x.UploadingUser = LoginHelper.GetUserName();
                x.FileTypeId = (int)FileType.FileType_10000003;

                byte[] bytes = null;

                if (Path.GetExtension(primaryFileName) != null && Path.GetExtension(primaryFileName).ToLower() == ".zip")
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, Path.GetFileNameWithoutExtension(primaryFileName), x.FileName));
                }
                else
                {
                    bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CustomCaseFiles, x.FileName));
                }

                result = InvestigationClueEvidenceFileService.Instance.CreateUpdate(x, bytes);
            });

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

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        private PostResponse CheckFileUploading()
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
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult List()
        {
            var model = new Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue.File.FileListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            return PartialView("PartialView/List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public JsonResult Files(string evidenceGuid, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationFiles = new List<BizInvestigationClueEvidenceFile>();

            if (!string.IsNullOrEmpty(evidenceGuid))
            {
                investigationFiles = InvestigationClueEvidenceFileService.Instance.GetInvestigationClueEvidenceFileList(evidenceGuid);
            }

            var result = new BizInvestigationClueEvidenceFileSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationFiles.Count;

            result.InvestigationClueFiles = investigationFiles.Any()
                    ? investigationFiles.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.FileId)
                        .ToList()
                    : new List<BizInvestigationClueEvidenceFile>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult Delete(List<long> fileIds)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvestigationClueEvidenceFileService.Instance.Delete(fileIds);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueEvidenceFileController.Delete", "InvestigationClueEvidenceFileController.Delete", ex);
                throw;
            }

            return Json(response);
        }
        /// <summary>
        /// 
        /// </summary>
        /// <param name="fileId"></param>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationClueEvidenceFileDownload(long fileId)
        {
            try
            {
                var investigationFile = InvestigationClueEvidenceFileService.Instance.GetInvestigationClueEvidenceFile(fileId);

                if (investigationFile != null)
                {
                    StringWriter strWriter = null;
                    HtmlTextWriter htmlWriter = null;

                    // 设置编码和附件格式  
                    Response.Charset = "gb2312";
                    Response.ContentEncoding = Encoding.GetEncoding("gb2312");
                    //Response.ContentType = "application/vnd.ms-word";

                    Response.AppendHeader("Content-Disposition", "attachment;filename=" +
                                                                 HttpUtility.UrlEncode(investigationFile.FileName, Encoding.UTF8)
                                                                     .ToString());

                    // 返回客户端  
                    var path = Path.Combine(FileHelper.InvestigationClueFiles, investigationFile.ClueGuid, investigationFile.FileName);
                    var bytes =
                        FileHelper.ReadFile(path);

                    if (bytes == null)
                    {
                        bytes = new byte[0];
                    }
                    return File(bytes, "attachment;filename=" + investigationFile.FileName);
                }
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueFileController.InvestigationClueEvidenceFileDownload", "InvestigationClueFileController.InvestigationClueEvidenceFileDownload", ex);
            }

            return null;
        }



        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationClueEvidenceFileList()
        {
            var model = new InvestigationClueEvidenceFileListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            return View("InvestigationClueEvidenceFileList", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult GetInvestigationClueEvidenceFileList(InvestigationClueEvidenceFileListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                var result = new BizInvestigationClueEvidenceFileSearchResultInfo();

                result.InvestigationClueFiles = InvestigationClueEvidenceFileService.Instance.GetInvestigationClueEvidenceFileList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueEvidenceFileService.GetInvestigationClueEvidenceFileList:", "InvestigationClueEvidenceFileService.GetInvestigationClueEvidenceFileList出错:", ex);
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

    }
}
