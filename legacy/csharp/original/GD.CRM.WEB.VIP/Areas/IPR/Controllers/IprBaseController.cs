using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Web;
using System.Web.Mvc;
using Dchien.Legal.Entity;
using Dchien.Legal.Service.IPR.Case;
using Dchien.Legal.Web.Areas.IPR.ViewModels;
using Dchien.Legal.Web.Areas.IPR.ViewModels.IprBase;
using Dchien.Legal.Service;


namespace Dchien.Legal.Web.Areas.IPR.Controllers
{
    /// <summary>
    ///
    /// </summary>
  
    public class IprBaseController : Controller
    {  
        /// <summary>
        /// 
        /// </summary>
        /// <param name="caseTypeId"></param>
        /// <returns></returns>
        [HttpPost]
        public ActionResult CaseFeeTypeList(int? caseTypeId)
        {
            var model = new CaseFeeTypeListModel();

            if (caseTypeId.HasValue)
            {
                var caseType = CaseTypeService.Instance.GetCaseType(caseTypeId.Value);
                if (caseType != null)
                {
                    model.CaseFeeTypes =  caseType.CaseFeeTypeList;
                    return PartialView(model);
                }
            }

            model.CaseFeeTypes = CaseTypeService.Instance.GetAllCaseFeeTypes();
            return PartialView(model);
        }
    }
}
