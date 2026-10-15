using Dchien.Legal.Entity.TP.Task;

namespace Dchien.Legal.Web.Areas.TP.ViewModels.Task
{
    public class ListModel 
	{

        public ListModel()
        {
            this.SearchCondition = new TaskSearchCondition();
        }

        public TaskSearchCondition SearchCondition { get; set; }

        /// <summary>
        /// 
        /// </summary>
        public int TaskTypeId { get; set; }

        public long? TaskId { get; set; }

        public int PendingCount { get; set; }

        public int ProcessingCount { get; set; }

        public int FinishedCount { get; set; }

        public int CheckedCount { get; set; }

        public int RejectedCount { get; set; }
        
       
	}
}
