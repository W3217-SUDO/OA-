using System.Collections.Generic;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case
{
    public class CaseClueListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizInvestigationClue> CaseClues { get; set; }

 

	}
}

