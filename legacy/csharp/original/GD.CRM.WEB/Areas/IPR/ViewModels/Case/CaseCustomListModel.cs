using System.Collections.Generic;
using Dchien.Legal.BizModel.IPR.Case;

namespace Dchien.Legal.Web.Areas.IPR.ViewModels.Case
{
    public class CaseCustomListModel 
	{

        /// <summary>
        /// 
        /// </summary>
        public string Keyword { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public List<BizCase> CaseList { get; set; }
 
	}
}





