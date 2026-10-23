using System;
using System.Collections.Generic;
using System.Linq;
using System.Web.Mvc;
using System.Text;
using System.IO;

using Dchien.Legal.Common;
using Dchien.Legal.Entity.BAS.Type;
using Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;
using Dchien.Legal.Service;
using Dchien.Legal.Service.Legal.Investigation;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;
using Dchien.Legal.Service.Legal.Investigation.Clue;
using Dchien.Legal.Entity.Legal.Investigation.Clue;
using Dchien.Legal.Web.Areas.Legal.ViewModels.Case;

namespace Dchien.Legal.Web.Areas.Legal.Controllers
{
    [CheckUserLogin]
    public class CaseClueController : BaseController
    {
        internal Log Logger = new Log("Legal.Controllers.CaseClueController");

        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseNo"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseClueList(string caseNo, int? pageNo, int? pageSize)
        {
            var caseClueListModel = new CaseClueListModel();

            var searchCondition = new InvestigationClueSearchCondition();
            searchCondition.CaseNo = caseNo;
            searchCondition.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            searchCondition.PageSize = pageSize.HasValue ? pageSize.Value : 15;

            caseClueListModel.CaseClues = InvestigationClueService.Instance.GetInvestigationClueList(searchCondition);
            caseClueListModel.TotalCount = searchCondition.TotalCount;
            caseClueListModel.PageNo = searchCondition.PageNo;
            caseClueListModel.PageSize = searchCondition.PageSize;

            return PartialView("ClueList", caseClueListModel);
        }
 
    }
}
