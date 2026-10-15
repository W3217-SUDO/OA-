using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Entity.Infrastructure;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using System.Web.UI;
using System.Web.UI.WebControls;
using Dchien.Legal.BizModel.Lawsuit.Case;
using Dchien.Legal.Common;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;

namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class CaseLogController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.CaseLogController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseLogList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new CaseLogListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 10;

            if (caseId > 0)
            {
                caseModel.CaseLogs = CaseLogService.Instance.GetCaseLogs(caseId);
                caseModel.TotalCount = caseModel.CaseLogs.Count;
                caseModel.CaseLogs = caseModel.CaseLogs.Any()
                    ? caseModel.CaseLogs.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<BizCaseLog>();
            }

            return PartialView("CaseLogList", caseModel);
        }
    }
}
