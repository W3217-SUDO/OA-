using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Entity.CRM.LawFirm;


namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseLawFirmSelectedModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizLawFirm> Customers { get; set; }

        public LawFirmSearchCondition SearchCondition { get; set; }

        public long CaseId { get; set; }

	}
}





