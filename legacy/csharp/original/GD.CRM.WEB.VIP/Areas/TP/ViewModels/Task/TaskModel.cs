using System.Collections.Generic;

using Dchien.Legal.Entity.TP.Task;
using Dchien.Legal.BizModel.TP.Task;

namespace Dchien.Legal.Web.Areas.TP.ViewModels.Task
{
    public class TaskModel
    {

        public TaskModel()
        {
             
        }

        public string CaseNos { get; set; }

        public BizTask Task { get; set; }

        public BizTaskNode TaskNode { get; set; }


        public List<BizTaskMessage> Messages { get; set; }

        /// <summary>
        /// 
        /// </summary>

        public string ErrorMessages { get; set; }
       
	}
}
