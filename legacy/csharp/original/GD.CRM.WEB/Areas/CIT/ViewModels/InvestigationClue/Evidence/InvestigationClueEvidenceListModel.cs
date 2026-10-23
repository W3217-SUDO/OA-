using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue
{
    public class InvestigationClueEvidenceListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public InvestigationClueSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public InvestigationClueEvidenceListModel()
        {
            this.SearchCondition = new InvestigationClueSearchCondition();
            this.SearchCondition.PageNo = 1;
            this.SearchCondition.PageSize = 15;
        }
    }
}
