using System;
using System.Collections.Generic;
using System.Linq;
using System.Web;
using System.Web.Mvc;

using Dchien.Legal.BizModel;
using Dchien.Legal.BizModel.Lawsuit.Case;

namespace Dchien.Legal.Web.Areas.Lawsuit.ViewModels.Case
{
    public class CaseCategoryListModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public List<BizCaseCategoryType> CaseCategoryTypeList { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int? CaseCategoryTypeId { get; set; }
	}
}





