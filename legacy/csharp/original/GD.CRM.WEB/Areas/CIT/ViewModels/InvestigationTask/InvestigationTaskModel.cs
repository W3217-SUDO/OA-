using Dchien.Legal.BizModel.Legal.Investigation.Task;
using Dchien.Legal.BizModel.Legal.Investigation;

namespace Dchien.Legal.Web.Areas.CIT.ViewModels.InvestigationTask
{
    public class InvestigationTaskModel 
	{
        /// <summary>
        /// 
        /// </summary>
        public int? TaskId { get; set; }
        /// <summary>
        /// 
        /// </summary>
        public BizInvestigationTask InvestigationTask { get; set; }


        public BizInvestigation Investigation { get; set; }
    }
}
