using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Investigation;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.Investigation
{
    public class InvestigationListModel : BaseListModel
    {
        /// <summary>
        /// 
        /// </summary>
	    public InvestigationSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public InvestigationListModel()
        {
            this.SearchCondition = new InvestigationSearchCondition();
            this.SearchCondition.PageNo = 1;
            this.SearchCondition.PageSize = 15;
        }
    }
}

