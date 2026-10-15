using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;

using Dchien.ServiceStack.Common.Extensions;
using Dchien.Legal.BizModel.Legal.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service.Legal.Case;
using Dchien.Legal.Service.FCM.Contract;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Service.BAS.Type;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CasePhaseController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CasePhaseController");

        [HttpPost]
        public JsonResult GetCasePhaseList(string id, int caseTypeId)
        {
            var response = new PostResponse();

            try
            {
                var phaseCaseCounts = CaseSearchService.Instance.GetCaseCountGroupbyCasePhase(id, caseTypeId);
                response.Data = new { PhaseCaseCounts = phaseCaseCounts};
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CasePhaseController.GetCasePhaseList", "CasePhaseController.GetCasePhaseList", ex);
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
        public JsonResult GetCasePhaseListForChange(int caseTypeId)
        {
            var response = new PostResponse();

            try
            {
                var casePhaseList = CasePhaseService.Instance.GetCasePhases(caseTypeId);
                response.Data = new { CasePhaseList = casePhaseList };
                response.IsSuccess = true;
            }
            catch (ApplicationException ex)
            {
                response.Message = ex.Message;
                response.IsSuccess = false;
            }
            catch (Exception ex)
            {
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CasePhaseController.GetCasePhaseListForChange", "CasePhaseController.GetCasePhaseListForChange", ex);
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
        public ActionResult CasePhaseEdit()
        {
            return PartialView("PartialView/CasePhaseEdit");
        }
    }
}
