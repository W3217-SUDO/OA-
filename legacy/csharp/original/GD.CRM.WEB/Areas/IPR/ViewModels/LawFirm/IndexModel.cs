using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using SunHold.Legal.BizModel;
using SunHold.Legal.BizModel.IPR.LawFirm;
using SunHold.Legal.Entity.IPR.LawFirm;

namespace SunHold.Legal.Web.Areas.IPR.ViewModels.LawFirm
{
    public class IndexModel 
	{
        public List<BizLawFirmType> CaseLawFirmTypeList { get; set; }

        public IndexModel()
        {
            this.SearchCondition = new LawFirmSearchCondition();
        }
        public LawFirmSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int LawFirmTypeId { get; set; }
	}
}





