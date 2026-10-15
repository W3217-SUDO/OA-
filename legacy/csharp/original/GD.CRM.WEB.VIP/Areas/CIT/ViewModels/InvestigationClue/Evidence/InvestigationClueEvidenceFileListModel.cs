using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Investigation.Clue;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationClue
{
    public class InvestigationClueEvidenceFileListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public InvestigationClueEvidenceFileSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public InvestigationClueEvidenceFileListModel()
        {
            this.SearchCondition = new InvestigationClueEvidenceFileSearchCondition();
            this.SearchCondition.PageNo = 1;
            this.SearchCondition.PageSize = 15;
        }
    }
}
