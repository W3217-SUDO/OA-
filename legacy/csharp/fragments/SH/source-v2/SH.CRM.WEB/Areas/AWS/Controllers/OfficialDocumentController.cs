using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Text;
using System.IO;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.AWS.OfficialDocument;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocument;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.AWS.OfficialDocument;
using Dchien.Legal.Web.Areas.AWS.ViewModels.OfficialDocumentAudit;
using Dchien.Legal.Service.AWS.OfficialDocument.Audit;
using Dchien.Legal.Entity.System;
using Dchien.Legal.Entity.AWS.OfficialDocument;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.AWS.OfficialDocument.File;
using Dchien.Legal.Service.FCM.Contract.File;
using Dchien.Legal.Service.Legal.Case;

namespace Dchien.Legal.Web.Areas.AWS.Controllers
{
    [CheckUserLogin]
    public class OfficialDocumentController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.OfficialDocumentController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult List(string id)
        {
            var model = new OfficialDocumentListModel();
            model.PageSize = 15;
            model.PageNo = 1;
            model.SearchCondition.PageId = id;

            if (id == PageId.PageId_8101001001  )
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
            }
            else if (id == PageId.PageId_8101001002  )
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101001003)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
            }
            else if (id == PageId.PageId_8101001004)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
            }
            else if(id == PageId.PageId_8101002001)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
            }
            else if (id == PageId.PageId_8101002002)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101002003)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
            }
            else if (id == PageId.PageId_8101003001)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
            }
            else if (id == PageId.PageId_8101003002)
            {
                model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
            }


            return View("List", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="request"></param>
        /// <param name="needToAudit"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult CreateUpdate(OfficialDocumentCreateModel request, bool needToAudit)
        {
            var response = new PostResponse();
            var officialDocument = new BizOfficialDocument();
            officialDocument.Basic = request.OfficialDocument;
            bool result = OfficialDocumentService.Instance.CreateUpdate(officialDocument);
            if (result)
            {
                response.Message = "提交成功！";
                response.IsSuccess = true;
            }
            else
            {
                response.Message = "提交失败！";
                response.IsSuccess = false;
            }

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="model"></param>
        /// <returns></returns>
        [HttpPost]
        [CheckUserLogin]
        public JsonResult List(OfficialDocumentListModel model)
        {
            var response = new PostResponse();

            try
            {
                if (model.SearchCondition.PageNo == 0)
                    model.SearchCondition.PageNo = 1;
                if (model.SearchCondition.PageSize == 0)
                    model.SearchCondition.PageSize = 15;

                if (model.SearchCondition.PageId == PageId.PageId_8101001001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001003)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001004)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101001005)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.W;
                    model.SearchCondition.BusinessOwner = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.P;
                    //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                    //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101002003)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.R;
                    //model.SearchCondition.Auditor = LoginHelper.GetUserName();
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101003001)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.E;
                }
                else if (model.SearchCondition.PageId == PageId.PageId_8101003002)
                {
                    model.SearchCondition.OfficialDocumentStatus = (int)OfficialDocumentStatus.N;
                }

                var result = new BizOfficialDocumentSearchResultInfo();

                result.OfficialDocuments = OfficialDocumentService.Instance.GetOfficialDocumentList(model.SearchCondition);

                result.TotalItemCount = model.SearchCondition.TotalCount;
                result.PageNo = model.SearchCondition.PageNo;
                result.PageSize = model.SearchCondition.PageSize;

                response.IsSuccess = true;
                response.Data = result;
            }
            catch (Exception ex)
            {
                response.IsSuccess = false;
                response.Message = "查询出错";
            }
            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Create(string id)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = new BizOfficialDocument();
            model.OfficialDocument.Basic = new BizOfficialDocumentBasic();
            model.OfficialDocument.Basic.OfficialDocumentGuid = Guid.NewGuid().ToString();
            model.OfficialDocument.Basic.OfficialDocumentBeginDate = DateTime.Now;

            return PartialView("PartialView/Create", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="contractNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult CreateByContract(string id,string contractNo, string contractFileIds)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = new BizOfficialDocument();
            model.OfficialDocument.Basic = new BizOfficialDocumentBasic();
            model.OfficialDocument.Basic.OfficialDocumentGuid = Guid.NewGuid().ToString();
            model.OfficialDocument.Basic.OfficialDocumentBeginDate = DateTime.Now;
            model.OfficialDocument.Basic.ContractNo = contractNo;
            var contract = ContractService.Instance.GetContractByNo(contractNo);
            model.OfficialDocument.Basic.CustomerNo = contract.ContractBasicInfo.CustomerNo;
            model.OfficialDocument.Basic.CustomerName = contract.ContractBasicInfo.CustomerName;
            var lst = new List<BizOfficialDocumentFile>();
            if (!string.IsNullOrEmpty(contractFileIds))
            {
                contractFileIds.Split(',').ToList().ForEach(fileId =>
                {
                    var contractFile = ContractFileService.Instance.GetContractFile(fileId);
                    var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ContractFiles, contractFile.ContractGuid, contractFile.FileName));
                    int fileSize = bytes == null ? 0:bytes.Length;
                    var officialDocumentFile = new BizOfficialDocumentFile();
                    officialDocumentFile.Uploader = LoginHelper.GetUserName();
                    officialDocumentFile.FileName = contractFile.FileName;
                    officialDocumentFile.FileSize = bytes == null ? 0 : bytes.Length;
                    officialDocumentFile.FileGuid = Guid.NewGuid().ToString();
                    officialDocumentFile.OfficialDocumentGuid = model.OfficialDocument.Basic.OfficialDocumentGuid;
                    officialDocumentFile.UploadTime = DateTime.Now;
                    OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes);
                    lst.Add(officialDocumentFile);
                });
            }
            else
            {
                var contractFiles = ContractFileService.Instance.GetContractFileListByContractNo(contractNo);
                if (null != contractFiles && contractFiles.Any())
                {
                    contractFiles.ForEach(contractFile => {
                        var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.ContractFiles, contractFile.ContractGuid, contractFile.FileName));
                        int fileSize = bytes == null ? 0 : bytes.Length;
                        var officialDocumentFile = new BizOfficialDocumentFile();
                        officialDocumentFile.Uploader = LoginHelper.GetUserName();
                        officialDocumentFile.FileName = contractFile.FileName;
                        officialDocumentFile.FileSize = bytes == null ? 0 : bytes.Length;
                        officialDocumentFile.FileGuid = Guid.NewGuid().ToString();
                        officialDocumentFile.OfficialDocumentGuid = model.OfficialDocument.Basic.OfficialDocumentGuid;
                        officialDocumentFile.UploadTime = DateTime.Now;
                        OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes);
                        lst.Add(officialDocumentFile);
                    });
                }
            }
            model.OfficialDocument.OfficialDocumentFileList = lst;
            return PartialView("PartialView/CreateByContract", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="contractNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult CreateByCase(string id, string caseNo, string caseFileIds)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = new BizOfficialDocument();
            model.OfficialDocument.Basic = new BizOfficialDocumentBasic();
            model.OfficialDocument.Basic.OfficialDocumentGuid = Guid.NewGuid().ToString();
            model.OfficialDocument.Basic.OfficialDocumentBeginDate = DateTime.Now;
            model.OfficialDocument.Basic.CaseNo = caseNo;
            var c = CaseService.Instance.GetCaseBasic(caseNo);
            model.OfficialDocument.Basic.ContractNo = c.Basic.ContractNo;
            model.OfficialDocument.Basic.CustomerNo = c.Basic.CustomerNo;
            model.OfficialDocument.Basic.CustomerName = c.Basic.CustomerName;
            if (!string.IsNullOrEmpty(caseFileIds))
            {
                var lst = new List<BizOfficialDocumentFile>();
                caseFileIds.Split(',').ToList().ForEach(fileId =>
                {
                    var caseFile = CaseFileService.Instance.GetCaseFile(long.Parse(fileId));
                    var bytes = FileHelper.ReadFile(Path.Combine(FileHelper.CaseFiles, c.Basic.CaseNo, caseFile.FileName));
                    var officialDocumentFile = new BizOfficialDocumentFile();
                    officialDocumentFile.Uploader = LoginHelper.GetUserName();
                    officialDocumentFile.FileName = caseFile.FileName;
                    officialDocumentFile.FileSize = bytes == null ? 0 : bytes.Length;
                    officialDocumentFile.FileGuid = Guid.NewGuid().ToString();
                    officialDocumentFile.OfficialDocumentGuid = model.OfficialDocument.Basic.OfficialDocumentGuid;
                    officialDocumentFile.UploadTime = DateTime.Now;
                    OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes);
                    lst.Add(officialDocumentFile);
                });
                model.OfficialDocument.OfficialDocumentFileList = lst;
            }
            return PartialView("PartialView/CreateByCase", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Preview(string id, string officialDocumentNo)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
            return PartialView("PartialView/Preview", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public ActionResult Edit(string id, string officialDocumentNo)
        {
            var model = new OfficialDocumentModel();
            model.OfficialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
            return PartialView("PartialView/Edit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult AuditList(string id, string officialDocumentNo)
        {
            var model = new AuditListModel();
            model.OfficialDocumentAuditList = OfficialDocumentAuditService.Instance.GetOfficialDocumentAuditList(officialDocumentNo);
            return PartialView("PartialView/Audit", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNo"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult GetOfficialDocument(string officialDocumentNo)
        {
            var response = new PostResponse();

            try
            {
                var officialDocument = OfficialDocumentService.Instance.GetOfficialDocument(officialDocumentNo);
                response.Data = officialDocument;
                response.IsSuccess = true;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "OfficialDocumentController.GetOfficialDocument", "OfficialDocumentController.GetOfficialDocument", ex);
                response.IsSuccess = false;
                response.Message = "查询出错.";
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult Print(List<string> officialDocumentNos)
        {
            var response = new PostResponse();
            OfficialDocumentService.Instance.Print(officialDocumentNos);
            response.Message = "用印成功！";
            response.IsSuccess = true;
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult Download(List<string> officialDocumentNos)
        {
            var response = new PostResponse();
            try
            {
                var fileName = OfficialDocumentService.Instance.Download(officialDocumentNos);
                response.Data = new { FileName = fileName };
                response.Message = "下载成功！";
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "OfficialDocumentController.Download", "OfficialDocumentController.Download", ex);
                throw;
            }
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="officialDocumentNos"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult Rollback(List<string> officialDocumentNos)
        {
            var response = new PostResponse();
            OfficialDocumentService.Instance.Rollback(officialDocumentNos);
            response.Message = "用印撤回成功！";
            response.IsSuccess = true;
            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult FileUpload()
        {
            return PartialView("PartialView/FileUpload");
        }

        [HttpPost]
        public JsonResult StampFileUpload(string officialDocumentNos)
        {
            var response = new PostResponse();
            var file =  Request.Files.Keys.Count == 0  ? null : Request.Files[0];
            //if (file == null)
            //{
            //    response.Message = "请选择文件进行上传.";
            //    response.IsSuccess = false;
            //    return Json(response);
            //}
            try
            {
                if (file != null)
                {
                    int fileSize = file.ContentLength;
                    var bytes = new byte[fileSize];
                    using (var stream = file.InputStream)
                    {
                        stream.Read(bytes, 0, fileSize);
                    }
                    officialDocumentNos.Split(',').ToList().ForEach(x =>
                    {
                        var officialDocument = OfficialDocumentService.Instance.GetOfficialDocument(x);
                        var officialDocumentFile = new BizOfficialDocumentFile();
                        officialDocumentFile.Uploader = LoginHelper.GetUserName();
                        officialDocumentFile.FileName = file.FileName;
                        officialDocumentFile.FileSize = fileSize;
                        officialDocumentFile.FileGuid = Guid.NewGuid().ToString();
                        officialDocumentFile.OfficialDocumentGuid = officialDocument.Basic.OfficialDocumentGuid;
                        officialDocumentFile.UploadTime = DateTime.Now;
                        OfficialDocumentFileService.Instance.CreateUpdate(officialDocumentFile, bytes);
                    });
                }

                OfficialDocumentService.Instance.Print(officialDocumentNos.Split(',').ToList());
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "StampFileUpload", "StampFileUpload", ex);
                response.Message = "用印失败.";
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
