using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.CRM.LawFirm;
using Dchien.Legal.Entity.CRM.LawFirm;

namespace Dchien.Legal.Web.Areas.CRM.ViewModels.LawFirm
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





