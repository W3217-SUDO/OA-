using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Mvc;
using Dchien.Legal.BizModel.FAM;
using Dchien.Legal.BizModel.FAM.AP.CaseFee;
using Dchien.Legal.Common;
using Dchien.Legal.Service.FAM.AP.CaseFee;
using Dchien.Legal.Service.FAM.Invoice;
using Dchien.Legal.Service.Lawsuit.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case;
using Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AP;
using Dchien.Legal.Web.Controllers;
using Dchien.Legal.Web.Models;


namespace Dchien.Legal.Web.Areas.Lawsuit.Controllers
{
    [CheckUserLogin]
    public class APCaseFeeController : BaseController
    {
        internal Log Logger = new Log("Lawsuit.Controllers.APCaseFeeController");

        /// <summary>
        ///  案件费用列表
        /// </summary>
        /// <param name="caseId"></param>
        /// <param name="pageNo"></param>
        /// <param name="pageSize"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeList(long caseId, int? pageNo, int? pageSize)
        {
            var caseModel = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AP.CaseFeeListModel();
            caseModel.PageNo = pageNo.HasValue ? pageNo.Value : 1;
            caseModel.PageSize = pageSize.HasValue ? pageSize.Value : 15;
            if (caseId > 0)
            {
                caseModel.CaseFeeList = Dchien.Legal.Service.FAM.AP.CaseFee.CaseFeeService.Instance.GetCaseFeeListByCaseId(caseId);
                caseModel.TotalCount = caseModel.CaseFeeList.Count;
                caseModel.CaseFeeList = caseModel.CaseFeeList.Any()
                    ? caseModel.CaseFeeList.Skip(caseModel.PageSize * (caseModel.PageNo - 1))
                        .Take(caseModel.PageSize)
                        .ToList()
                    : new List<Dchien.Legal.BizModel.FAM.AP.CaseFee.BizCaseFee>();
            }
            return PartialView("CaseFeeList", caseModel);
        }


   
        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseFeeIds"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult PaymentApply(List<long> caseFeeIds)
        {
            var caseModel = new Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case.AR.CaseFeeListModel();

            caseModel.CaseFeeList = Dchien.Legal.Service.FAM.AR.CaseFee.CaseFeeService.Instance.GetCaseFeeListByCaseFeeIds(caseFeeIds);

            return PartialView("PaymentApply", caseModel);
        }
    }
}
