using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.BizModel.CRM.Customer;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Common;
using Dchien.Legal.Entity;
using Dchien.Legal.Entity.IPR.Case;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Service.IPR.CaseFileProcess;
using Dchien.Legal.Web.Areas.IPR.Controllers;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.Case;
using Dchien.Legal.Web.Areas.CRM.ViewModels.Customer;
using Dchien.Legal.Service;
using Dchien.Legal.Service.CRM.Customer;
using Dchien.Legal.Service.CRM.LawFirm;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    [CheckUserLogin]
    public class CaseLogController : BaseController
    {
        internal Log Logger = new Log("IPR.Controllers.CaseLogController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseLogId"></param>
        /// <returns></returns>
        [HttpPost]
        public JsonResult CaseLogDelete(long caseLogId)
        {
            var response = new PostResponse();

            try
            {
                bool result = CaseLogService.Instance.CaseLogDelete(caseLogId);

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
                Logger.Error(LoginHelper.GetClientIP(), LoginHelper.GetUserName(), "CaseController.CaseLogDelete", "CaseController.CaseLogDelete", ex);
                throw;
            }

            return Json(response);
        }
    }
}
