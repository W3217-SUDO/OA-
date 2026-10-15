using Dchien.Legal.Web.Models;
using Dchien.Legal.Entity.Legal.Investigation.Task;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationTask
{
    public class InvestigationTaskListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public InvestigationTaskSearchCondition SearchCondition { get; set; }


        /// <summary>
        /// 
        /// </summary>
        public InvestigationTaskListModel()
        {
            this.SearchCondition = new InvestigationTaskSearchCondition();
            this.SearchCondition.PageNo = 1;
            this.SearchCondition.PageSize = 15;
        }
    }
}
