using System.Collections.Generic;
using Dchien.Legal.Web.Models;
using Dchien.Legal.BizModel.TP.Task;


namespace Dchien.Legal.Web.Areas.Legal.ViewModels.Case
{
    public class CaseTaskListModel : BaseListModel
	{
        /// <summary>
        /// 
        /// </summary>
	    public List<BizTask> CaseTasks { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public long CaseId { get; set; }
 

	}
}

