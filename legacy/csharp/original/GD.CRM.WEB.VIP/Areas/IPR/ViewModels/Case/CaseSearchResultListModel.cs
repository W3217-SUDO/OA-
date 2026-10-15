using System.Collections.Generic;
using Dchien.Legal.BizModel.IPR.Case;
using Dchien.Legal.Entity.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseSearchResultListModel 
	{
        public CaseSearchCondition SearchCondition { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> CaseList { get; set; }
 
	}
}
