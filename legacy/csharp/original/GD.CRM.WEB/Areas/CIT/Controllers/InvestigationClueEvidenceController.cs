using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.IO;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.BizModel.Legal.Investigation.Evidence;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Entity.Legal.Investigation.Clue;
using Dchien.Legal.Service.BAS.Warehouse;

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationClueEvidenceController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueEvidenceController");
 
        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Create(string id, string investigationClueNo)
        {
            var model = new InvestigationClueEvidenceModel();
            model.InvestigationClueEvidence = new BizModel.Legal.Investigation.Evidence.BizInvestigationClueEvidence();
            model.InvestigationClueEvidence.Basic = new BizModel.Legal.Investigation.Evidence.BizInvestigationClueEvidenceBasic();

            var clue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);
            model.InvestigationClueEvidence.Basic.ClueGuid = clue.Basic.ClueGuid;
            model.InvestigationClueEvidence.Basic.EvidenceDate = DateTime.Now;
            //model.InvestigationClueEvidence.Basic.NotarialObtainDate = DateTime.Now;

            return PartialView("PartialView/Create", model);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult MultiCreate(string id, string investigationClueNo)
        {
            var model = new InvestigationClueEvidenceModel();
            model.InvestigationClueEvidence = new BizModel.Legal.Investigation.Evidence.BizInvestigationClueEvidence();
            model.InvestigationClueEvidence.Basic = new BizModel.Legal.Investigation.Evidence.BizInvestigationClueEvidenceBasic();

            var clue = InvestigationClueService.Instance.GetInvestigationClueBasic(investigationClueNo);
            model.InvestigationClueEvidence.Basic.ClueGuid = clue.Basic.ClueGuid;
            model.InvestigationClueEvidence.Basic.EvidenceDate = DateTime.Now;

            return PartialView("PartialView/MultiCreate", model);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <param name="evidenceGuid"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Edit(string id, string evidenceGuid)
        {
            var model = new InvestigationClueEvidenceModel();
            model.InvestigationClueEvidence =  InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidence(evidenceGuid);

            return PartialView("PartialView/Create", model);
        }


        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult CreateUpdate(InvestigationClueEvidenceModel model)
        {
            var response = new PostResponse();

            InvestigationClueEvidenceService.Instance.CreateUpdate(model.InvestigationClueEvidence);

            for (int i = 0; i < Request.Files.Count; i++)
            {
                var file = Request.Files[i];
                int fileSize = file.ContentLength;
                var bytes = new byte[fileSize];
                using (var stream = file.InputStream)
                {
                    stream.Read(bytes, 0, fileSize);
                }

                var investigationFile = new BizInvestigationClueEvidenceFile();
                investigationFile.EvidenceGuid = model.InvestigationClueEvidence.Basic.EvidenceGuid;
                investigationFile.ClueGuid = model.InvestigationClueEvidence.Basic.ClueGuid;
                investigationFile.FileTypeId = (int)FileType.FileType_10000003;
                investigationFile.UploadingUser = LoginHelper.GetUserName();
                investigationFile.FileName = file.FileName;
                investigationFile.FileSize = fileSize;
                investigationFile.UploadingTime = DateTime.Now;

                InvestigationClueEvidenceFileService.Instance.CreateUpdate(investigationFile, bytes);
            }

            response.Message = "取证成功！";
            response.IsSuccess = true;

            return Json(response);
        }


        /// <summary>
        /// 
        /// </summary>
        /// <param name="investigationClueNos"></param>
        /// <param name="model"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        [HttpPost]
        public JsonResult MultiCreateUpdate(List<string> investigationClueGuids, DateTime evidenceDate,string notaryOrganization,string notarialNo)
        {
            var response = new PostResponse();

            if (investigationClueGuids != null && investigationClueGuids.Any())
            {
                investigationClueGuids.ForEach(x =>
                {
                    var investigationClueEvidence = new BizInvestigationClueEvidence();
                    investigationClueEvidence.Basic = new BizInvestigationClueEvidenceBasic();
                    investigationClueEvidence.Basic.ClueGuid = x;
                    investigationClueEvidence.Basic.NotaryOrganization = notaryOrganization;
                    investigationClueEvidence.Basic.NotarialObtainDate = evidenceDate;
                    investigationClueEvidence.Basic.EvidenceDate = evidenceDate;
                    investigationClueEvidence.Basic.NotarialNo = notarialNo;
                    InvestigationClueEvidenceService.Instance.CreateUpdate(investigationClueEvidence);
                });
            }

            response.Message = "取证成功！";
            response.IsSuccess = true;

            return Json(response);
        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public ActionResult List()
        {
            var model = new InvestigationClueEvidenceListModel();
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
        public JsonResult InvestigationClueEvidences(string investigationClueGuid, int? pageNo, int? pageSize)
        {
            var response = new PostResponse();

            var investigationClueEvidences = new List<BizInvestigationClueEvidence>();

            if (!string.IsNullOrEmpty(investigationClueGuid))
            {
                investigationClueEvidences = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidenceList(investigationClueGuid);
            }

            var result = new BizInvestigationClueEvidenceSearchResultInfo();

            result.PageNo = pageNo > 0 ? pageNo.Value : 1;
            result.PageSize = pageSize > 0 ? pageSize.Value : 15;

            result.TotalItemCount = investigationClueEvidences.Count;

            result.InvestigationClueEvidences = investigationClueEvidences.Any()
                    ? investigationClueEvidences.Skip(result.PageSize * (result.PageNo - 1))
                        .Take(result.PageSize)
                        .OrderBy(x => x.Basic.EvidenceId)
                        .ToList()
                    : new List<BizInvestigationClueEvidence>();

            response.IsSuccess = true;
            response.Data = result;

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <returns></returns>
        [CheckUserLogin]
        public ActionResult InvestigationClueEvidenceAddIn()
        {
            return View("InvestigationClueEvidenceAddIn");
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
        public JsonResult InvestigationClueEvidenceAddInFileUpload()
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

            try
            {
                var lst = InvestigationClueEvidenceService.Instance.ProcessInvestigationClueEvidenceAddFileIn
                    (file.FileName, bytes);

                if (lst != null && lst.Any())
                {
                    response.Data = new { InvestigationClues = lst, PrimaryFileName = file.FileName };
                    response.Message = "上传成功！";
                    response.IsSuccess = true;
                }
                else
                {
                    response.Message = "未匹配上线索！";
                    response.IsSuccess = false;
                }
            }
            catch(ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueEvidenceController.InvestigationClueEvidenceAddInFileUpload", "InvestigationClueEvidenceController.InvestigationClueEvidenceAddInFileUpload", ex);
                response.Message = "文件格式不正确.";
                response.IsSuccess = false;
            }

            return Json(response);

        }

        /// <summary>
        /// 
        /// </summary>
        /// <param name="evidences"></param>
        /// <param name="primaryFileName"></param>
        /// <returns></returns>
        [CheckUserLogin]
        [HttpPost]
        public JsonResult InvestigationClueEvidenceAddInFileIn(List<BizInvestigationClueEvidenceBasic> evidenceAddIns, string primaryFileName)
        {
            var response = new PostResponse();

            bool result = true;

            if (evidenceAddIns != null && evidenceAddIns.Any())
            {
                var warehouses = WarehouseService.Instance.GetAllWarehousesFromDb();
                var locations = WarehouseStorageLocationService.Instance.GetAllWarehouseStorageLocationsFromDb();

                evidenceAddIns.ForEach(x =>
                {
                    var evidence = InvestigationClueEvidenceService.Instance.GetInvestigationClueEvidence(x.EvidenceGuid);
                    evidence.Basic.NotarialNo = x.NotarialNo;
                    evidence.Basic.DepositAddress = x.DepositAddress;
                    evidence.Basic.StorageLocationName = x.DepositAddress;
                    if (!string.IsNullOrEmpty(x.WarehouseName))
                    {
                        evidence.Basic.WarehouseNo = warehouses.FirstOrDefault(w => w.WarehouseName == x.WarehouseName).WarehouseNo;
                    }
                    if (!string.IsNullOrEmpty(x.DepositAddress))
                    {
                        evidence.Basic.StorageLocationNo = locations.FirstOrDefault(w => w.StorageLocationName == x.DepositAddress).StorageLocationNo;
                        evidence.Basic.EvidenceStatus = (int)InvestigationClueEvidenceStatus.Inbound;
                    }
                    evidence.Basic.InvoiceNo = x.InvoiceNo;
                    InvestigationClueEvidenceService.Instance.CreateUpdate(evidence);
                });
            }

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
        /// <param name="clueNos"></param>
        /// <returns></returns>

        [HttpPost]
        public JsonResult Delete(string evidenceGuid)
        {
            var response = new PostResponse();

            try
            {
                bool result = InvestigationClueEvidenceService.Instance.Delete(evidenceGuid);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "InvestigationClueEvidenceController.Delete", "InvestigationClueEvidenceController.Delete", ex);
                throw;
            }

            return Json(response);
        }
    }
}
