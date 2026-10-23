using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

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

namespace Dchien.Legal.Web.Areas.CIT.Controllers
{
    [CheckUserLogin]
    public class InvestigationClueIndicteeController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.InvestigationClueIndicteeController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        [AcceptVerbs(HttpVerbs.Post)]
        public ActionResult Create(string id)
        {
            var model = new InvestigationIndicteeModel();
            model.InvestigationClueIndictee = new BizInvestigationClueIndictee();
            return PartialView("Create", model);
        }

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
    }
}
