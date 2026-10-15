using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.LawFirm;


namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseLawFirmListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizLawFirm> CaseLawFirms { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }


	}
}





